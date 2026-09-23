# we are trying to imitate joan's matlab code to calculate Hsig and Tp 
# from mareograf series
# i want to make it operational for each day
# last modifies 21/09/26
###################^w^####################
# Triam els paràmetres

import sys
from pathlib import Path
from datetime import date, datetime, timedelta
import matplotlib.pyplot as plt

import numpy as np
import pandas as pd
import scipy.fftpack as fft
import xarray as xr
import yaml
from wave_functions import welch_periodogram

# ============================================================
# IMPORTANT PARAMETERS
# ============================================================

# sampling period of the sea level data
dt = 0.5

# Maximum fraction of NaNs allowed in each block
umbral_nan = 0.2  # 20%

# Sample lenght used for each wave parameters estimate
intervalo_muestras = 1024*4

# Time interval between wave parameters estimation
wave_dt='0.5h'

# number of sample per each window in the welch periodogram
n_fft_welch=256

# Valid limits of teh spectrum in period [s]
Tmin = 1
Tmax = 20

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
CASE = "tarragona"

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

output_file_w = (
    output_dir
    / f"wave_parameters{yesterday_str}_welch.txt"
)

# Overwrite outputs on every run.
output_file.unlink(missing_ok=True)
output_file_w.unlink(missing_ok=True)



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
# EXTRACT SEA LEVEL DATA
# ============================================================

SL = df["SLEV"].values
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
    freq=wave_dt
)


# ============================================================
# FFT PARAMETERS
# ============================================================

n_fft = 1024 // 2


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

Hm_w = np.zeros(len(timeVec))*np.nan
Tm1_w = np.zeros(len(timeVec))*np.nan
Tm2_w = np.zeros(len(timeVec))*np.nan
tp_w = np.zeros(len(timeVec))*np.nan

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
    if ind < len(time) - intervalo_muestras + 1:

        aux_raw = SL[
            ind:ind + intervalo_muestras
        ]

        nan_indices=np.where(~np.isnan(aux_raw))[0]
        if nan_indices.size == 0:
            aux_cut=aux_raw.copy()
        else:
            first_valid=nan_indices[0]
            last_valid=nan_indices[-1]

            aux_cut=aux_raw[first_valid:last_valid]
    
        nan_frac=np.isnan(aux_cut).sum()/len(aux_cut)
        # ----------------------------------------------------
        # FFT
        # ----------------------------------------------------
        if (nan_frac<=umbral_nan) & (len(aux_cut)>=n_fft):
            aux = (pd.Series(aux_cut)
                .interpolate(method="linear", limit_direction="both")
                .to_numpy())
            frequency,pwel=welch_periodogram(aux - np.mean(aux), dt, n_fft_welch, segment_length=n_fft_welch, overlap=0.5)

            m0_w = np.sum(
                        pwel
                    )
            
            m1_w = np.sum(
                pwel
                * frequency
            )

            m2_w = np.sum(
                pwel
                * (frequency ** 2)
            )

            # ----------------------------------------------------
            # Peak period
            # ----------------------------------------------------

            ind2 = np.argmax(
                spt_filt[n]
            )

            ind2_w = np.argmax(
                        pwel
                    )

            # ----------------------------------------------------
            # Wave parameters
            # ----------------------------------------------------

            Hm_w[n] = np.sqrt(m0_w) * 4

            Tm1_w[n] = (
                m0_w / m1_w
                if m1_w != 0
                else np.nan
            )

            Tm2_w[n] = (
                np.sqrt(m0_w / m2_w)
                if m2_w != 0
                else np.nan
            )

            tp_w[n] = 1/frequency[ind2_w]

        else:
            print(t_ref)
        # ----------------------------------------------------
        # Save result
        # ----------------------------------------------------

        result_df_w = pd.DataFrame({
            "TIME": [t_ref],
            "Hsig": [round(Hm_w[n], 8)],
            "Tp": [round(tp_w[n], 8)],
            "Tm1": [round(Tm1_w[n], 8)],
            "Tm2": [round(Tm2_w[n], 8)]
        })

        result_df_w["TIME"] = (
            result_df_w["TIME"]
            .dt.strftime("%Y-%m-%d %H:%M:%S")
        )

        # Append to output file
        result_df_w.to_csv(
            output_file_w,
            sep="\t",
            index=False,
            mode="a",
            header=not output_file_w.exists()
        )

        print(
            f"Results saved for {t_ref} "
            f"in {output_file_w}"
        )
    else:
        print(t_ref)

#%%
plt.figure(figsize=(15,15))
plt.subplot(411)
plt.plot(df.TIME,df.SLEV-3.1,color="grey",label="Origunal SL data")
plt.plot(timeVec,Hm_w,'.',label="Welch periodorgam")
plt.ylabel("Hm [m]")
plt.grid()
plt.legend()

plt.subplot(412)
plt.plot(timeVec,tp_w,'.',label="Welch periodorgam")
plt.ylabel("Peak Period [s]")
plt.grid()
plt.legend()

plt.subplot(413)
plt.plot(timeVec,Tm1_w,'.',label="Welch periodorgam")
plt.ylabel("Tm1 [s]")
plt.grid()
plt.legend()


plt.subplot(414)
plt.plot(timeVec,Tm2_w,'.',label="Welch periodorgam")
plt.ylabel("Tm2 [s]")
plt.grid()
plt.legend()

