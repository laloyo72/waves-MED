# we are trying to imitate joan's matlab code to calculate Hsig and Tp 
# from mareograf series
# i want to make it operational for each day
# last modifies 21/09/26
###################^w^####################
# Triam els paràmetres

import sys
from pathlib import Path
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import scipy.fftpack as fft
import xarray as xr
import yaml


# ============================================================
# CASE CONFIGURATION
# ============================================================

# Repository root
ROOT = Path(__file__).resolve().parents[2]

# Cases configuration
CASES_FILE = ROOT / "config" / "cases.yml"

# Base Puertos de Estado OPeNDAP server
BASE_OPENDAP = "http://opendap.puertos.es/thredds/dodsC"


def load_case(case_name):
    """Load configuration for a case from cases.yml."""

    with open(CASES_FILE, "r") as f:
        cases = yaml.safe_load(f)

    if case_name not in cases:
        available = ", ".join(cases.keys())
        raise ValueError(
            f"Unknown case '{case_name}'. "
            f"Available cases: {available}"
        )

    return cases[case_name]


# ============================================================
# SELECT CASE
# ============================================================

if len(sys.argv) != 2:
    print(
        "Usage:\n"
        "  python3 scripts/validation/"
        "download_and_calculate_mareograf_op.py <case>\n"
        "\n"
        "Example:\n"
        "  python3 scripts/validation/"
        "download_and_calculate_mareograf_op.py palma"
    )
    sys.exit(1)

CASE = sys.argv[1].lower()

case_config = load_case(CASE)

# Tide gauge configuration
tide_gauge = case_config.get("tide_gauge")

if tide_gauge is None:
    raise ValueError(
        f"Case '{CASE}' does not have a tide gauge configured "
        "in cases.yaml."
    )

GAUGE_CODE = tide_gauge["code"]
GAUGE_SUBDIR = tide_gauge["subdir"]

print("\n======================================")
print(f"CASE:        {CASE}")
print(f"Tide gauge:  {GAUGE_CODE}")
print(f"Directory:   {GAUGE_SUBDIR}")
print("======================================\n")


# ============================================================
# DATE
# ============================================================

today = date.today()
yesterday = today - timedelta(days=1)

yesterday_str = yesterday.strftime("%Y%m%d")

year = yesterday.year
month = yesterday.month
day = yesterday.day

print("Yesterday was:")
print(year, month, day)


# ============================================================
# INPUT / OUTPUT
# ============================================================

# Puertos OPeNDAP file
url = (
    f"{BASE_OPENDAP}/"
    f"{GAUGE_SUBDIR}/"
    f"{year}/{month:02d}/"
    f"{GAUGE_CODE}_{yesterday_str}.nc4"
)

print(f"\nDownloading:")
print(url)

# Output directory for this case
output_dir = (
    ROOT
    / "cases"
    / CASE
    / "validation"
    / "mareograf"
)

output_dir.mkdir(parents=True, exist_ok=True)

output_file = (
    output_dir
    / f"wave_parameters{yesterday_str}.txt"
)

print(f"Output file:")
print(output_file)


# ============================================================
# DOWNLOAD TIDE GAUGE DATA
# ============================================================

# Initialize lists to store data
time_list = []
slev_list = []

try:

    # Open dataset
    ds = xr.open_dataset(url)

    # Select only required variables
    vars = ds[["TIME", "SLEV"]]

    # Convert to dataframe
    df_download = vars.to_dataframe().reset_index()

    # Append data
    time_list.extend(df_download["TIME"].tolist())
    slev_list.extend(df_download["SLEV"].tolist())

    print(f"Data loaded for {yesterday_str}")

    ds.close()

except Exception as e:

    print(f"Error downloading dataset: {e}")
    sys.exit(1)


# ============================================================
# DATAFRAME FOR CALCULATION
# ============================================================

df = pd.DataFrame({
    "TIME": time_list,
    "SLEV": slev_list
})

df["TIME"] = pd.to_datetime(
    df["TIME"],
    utc=True
)


# ============================================================
# INTERPOLATION
# ============================================================

nan_indices = df["SLEV"].isna()

# Maximum fraction of NaNs allowed in each block
umbral_nan = 0.1  # 10%

# 8 minutes at 2 Hz = 960 samples
intervalo_muestras = 960

# Copy SLEV column
df["SLEV_interp"] = df["SLEV"].copy()


# Process in 8-minute blocks
for i in range(
    0,
    len(df) - intervalo_muestras,
    intervalo_muestras
):

    indices_intervalo = np.arange(
        i,
        i + intervalo_muestras
    )

    num_nans_intervalo = (
        nan_indices.iloc[indices_intervalo].sum()
    )

    num_datos_intervalo = len(indices_intervalo)

    # Interpolate if NaNs are below threshold
    if (
        num_nans_intervalo / num_datos_intervalo
        <= umbral_nan
    ):

        valid_data = (
            df.loc[
                indices_intervalo,
                "SLEV"
            ].dropna()
        )

        if len(valid_data) > 1:

            df.loc[
                indices_intervalo,
                "SLEV_interp"
            ] = (
                df.loc[
                    indices_intervalo,
                    "SLEV"
                ]
                .interpolate(
                    method="linear",
                    limit_direction="both"
                )
            )


# ============================================================
# EXTRACT SEA LEVEL DATA
# ============================================================

SL_interpolado = df["SLEV_interp"].values
time = df["TIME"].values


# ============================================================
# TIME VECTOR
# ============================================================

# One result per hour of yesterday
timeVec = pd.date_range(
    start=datetime.combine(
        yesterday,
        datetime.min.time()
    ),
    end=datetime.combine(
        yesterday,
        datetime.max.time()
    ),
    freq="1h"
)


# ============================================================
# FFT PARAMETERS
# ============================================================

n_fft = 1024 // 2

Tmin = 1
Tmax = 20

dt = 0.5

n_fmax = int(
    n_fft * dt / Tmin
)

n_fmin = int(
    np.floor(
        n_fft * dt / Tmax
    )
)


# ============================================================
# INITIALIZE RESULTS
# ============================================================

Hm = np.zeros(len(timeVec))
Tm1 = np.zeros(len(timeVec))
Tm2 = np.zeros(len(timeVec))
tp = np.zeros(len(timeVec))

spt_news = [None] * len(timeVec)
spt_filt = [None] * len(timeVec)


# ============================================================
# FFT PROCESSING
# ============================================================

for n, t_ref in enumerate(timeVec):

    # Find closest index in tide gauge time series
    t_ref_np = np.datetime64(t_ref)

    ind = np.argmin(
        np.abs(
            time - t_ref_np
        )
    )

    # Make sure enough data exists
    if ind < len(time) - n_fft + 1:

        aux = SL_interpolado[
            ind:ind + n_fft
        ]

        # ----------------------------------------------------
        # FFT
        # ----------------------------------------------------

        new_fft = fft.fft(
            aux - np.mean(aux),
            n_fft
        )

        new_spt = np.abs(
            new_fft
        ) ** 2

        new_spt = (
            2
            * new_spt
            / (n_fft ** 2)
        )

        # ----------------------------------------------------
        # Frequency filtering
        # ----------------------------------------------------

        new_spt[:n_fmin] = 0
        new_spt[n_fmax:] = 0

        new_freq = (
            np.arange(len(new_spt))
            / (n_fft * dt)
        )

        new_freq = new_freq[
            :n_fmax
        ]

        new_spt = new_spt[
            :n_fmax
        ]

        spt_news[n] = new_spt

        # ----------------------------------------------------
        # Spectral filtering
        # ----------------------------------------------------

        spt_filt[n] = new_spt * (1 - (1 / (1 + ((new_freq / (2 / Tmax)) ** 2) ** 2)))
        new_period = 1 / new_freq

        # ----------------------------------------------------
        # Spectral moments
        # ----------------------------------------------------

        m0 = np.sum(
            spt_filt[n]
        )

        m1 = np.sum(
            spt_filt[n]
            * new_freq
        )

        m2 = np.sum(
            spt_filt[n]
            * (new_freq ** 2)
        )

        # ----------------------------------------------------
        # Peak period
        # ----------------------------------------------------

        ind2 = np.argmax(
            spt_filt[n]
        )

        # ----------------------------------------------------
        # Wave parameters
        # ----------------------------------------------------

        Hm[n] = np.sqrt(m0) * 4

        Tm1[n] = (
            m0 / m1
            if m1 != 0
            else np.nan
        )

        Tm2[n] = (
            np.sqrt(m0 / m2)
            if m2 != 0
            else np.nan
        )

        tp[n] = new_period[ind2]

        # ----------------------------------------------------
        # Save result
        # ----------------------------------------------------

        result_df = pd.DataFrame({
            "TIME": [t_ref],
            "Hsig": [round(Hm[n], 8)],
            "Tp": [round(tp[n], 8)],
            "Tm1": [round(Tm1[n], 8)],
            "Tm2": [round(Tm2[n], 8)]
        })

        result_df["TIME"] = (
            result_df["TIME"]
            .dt.strftime("%Y-%m-%d %H:%M:%S")
        )

        # Append to output file
        result_df.to_csv(
            output_file,
            sep="\t",
            index=False,
            mode="a",
            header=not output_file.exists()
        )

        print(
            f"Results saved for {t_ref} "
            f"in {output_file}"
        )
