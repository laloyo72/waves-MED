# we are trying to adapt joan's matlab code to calculate Hsig, Tp, Tm1 and Tm2
# from mareograf series of Puertos
# generalized & interactive version for long-term use
# updated to use the same Welch methodology as the operational script
# 24/09/26
###################^w^####################

import numpy as np
import pandas as pd
import xarray as xr
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
import yaml

from wave_functions import welch_periodogram


# ============================================================
# CASES CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[2]
CASES_FILE = ROOT / "config" / "cases.yml"

BASE_OPENDAP = "http://opendap.puertos.es/thredds/dodsC"


# ============================================================
# WAVE PARAMETERS
# ============================================================

# Sampling period of the sea level data [s]
dt = 0.5

# Maximum fraction of NaNs allowed in each wave-analysis window
umbral_nan = 0.2  # 20%

# Sample length used for each wave parameter estimate
intervalo_muestras = 1024 * 4

# Time interval between wave parameter estimates
wave_dt = "0.5h"

# Number of samples per segment in the Welch periodogram
n_fft_welch = 256

# Valid limits of the spectrum in period [s]
Tmin = 1
Tmax = 20


# ============================================================
# CASES
# ============================================================

def load_cases():
    """Load case configuration from cases.yml."""
    with open(CASES_FILE, "r") as f:
        return yaml.safe_load(f)


def ask_inputs():
    print("\n=== Available Tide Gauges from PdE → Hsig/Tp ===\n")
    print(
        "We selected the tide gauges that are not directly inside the port, "
        "so that they represent the energy that can be obtained from the waves "
        "outside the port :3"
    )

    cases = load_cases()

    # Only show cases with a tide gauge configured
    available_gauges = {
        name: config
        for name, config in cases.items()
        if config.get("tide_gauge") is not None
    }

    print("Available ports:")
    for case in available_gauges:
        print(f" - {case}")

    station = input("\nSelect one: ").strip().lower()

    if station not in available_gauges:
        raise ValueError(f"'{station}' is not on the list.")

    print(
        "Recommendation: download at least 1 year of data "
        "to train TimeGPT module"
    )

    start_str = input("Start date (YYYY-MM-DD): ").strip()
    end_str = input("End date   (YYYY-MM-DD): ").strip()

    start_date = datetime.strptime(
        start_str, "%Y-%m-%d"
    ).replace(tzinfo=timezone.utc)

    end_date = datetime.strptime(
        end_str, "%Y-%m-%d"
    ).replace(tzinfo=timezone.utc)

    return station, start_date, end_date


# ============================================================
# DOWNLOAD SEA LEVEL DATA
# ============================================================

def load_puertos_series(station, start_date, end_date):

    cases = load_cases()

    tide_gauge = cases[station].get("tide_gauge")

    if tide_gauge is None:
        raise ValueError(
            f"No tide gauge is configured for case '{station}'."
        )

    code = tide_gauge["code"]
    subdir = tide_gauge["subdir"]

    current_date = start_date
    time_list, slev_list = [], []

    while current_date <= end_date:

        date_str = current_date.strftime("%Y%m%d")
        year, month = current_date.year, current_date.month

        url = (
            f"{BASE_OPENDAP}/{subdir}/{year}/{month:02d}/"
            f"{code}_{date_str}.nc4"
        )

        try:
            ds = xr.open_dataset(url)
            df_day = (
                ds[["TIME", "SLEV"]]
                .to_dataframe()
                .reset_index()
            )

            time_list.extend(df_day["TIME"].tolist())
            slev_list.extend(df_day["SLEV"].tolist())

            print(f"Data loaded for {date_str}")

        except Exception as e:
            print(f"Error loading data for {date_str}: {e}")

        current_date += timedelta(days=1)

    if len(time_list) == 0:
        print("\n⚠ No se ha podido cargar ningún dato de Puertos.")
        print("   Revisa manualmente el catálogo OPeNDAP:")
        print("   https://opendap.puertos.es/thredds/catalog/catalog.html")
        print("\n   Sin datos de mareógrafo no puedes usar este módulo :(\n")
        return None

    df = pd.DataFrame({
        "TIME": time_list,
        "SLEV": slev_list
    })

    df["TIME"] = pd.to_datetime(
        df["TIME"],
        utc=True
    )

    return df


# ============================================================
# CALCULATE WAVE PARAMETERS USING WELCH
# ============================================================

def calculate_wave_params(df, start_date, end_date, station):

    SL = df["SLEV"].values
    time = df["TIME"].values

    # One result every wave_dt over the requested period
    timeVec = pd.date_range(
        start=start_date,
        end=end_date,
        freq=wave_dt
    )

    # Initialize results
    Hm_w = np.full(len(timeVec), np.nan)
    Tm1_w = np.full(len(timeVec), np.nan)
    Tm2_w = np.full(len(timeVec), np.nan)
    tp_w = np.full(len(timeVec), np.nan)

    # YYYYMMDD for output filename
    start = start_date.strftime("%Y%m%d")
    end = end_date.strftime("%Y%m%d")

    outdir = (
        ROOT / "DATA" / "mareograf" / "calculated" / station
    )
    outdir.mkdir(parents=True, exist_ok=True)

    output_file = (
        outdir /
        f"wave_parameters_{station}_{start}_{end}_welch.csv"
    )

    # If it exists from a previous run, remove it to avoid mixing runs
    if output_file.exists():
        output_file.unlink()

    # ========================================================
    # WAVE PARAMETER CALCULATION
    # ========================================================

    for n, t_ref in enumerate(timeVec):

        # Find closest index in tide gauge time series
        t_ref_np = np.datetime64(
            t_ref.replace(tzinfo=None)
        )

        ind = np.argmin(
            np.abs(time - t_ref_np)
        )

        # Make sure enough data exists for a complete analysis window
        if ind >= len(time) - intervalo_muestras + 1:
            print(t_ref)
            continue

        # Extract analysis window
        aux_raw = SL[
            ind:ind + intervalo_muestras
        ]

        # Remove leading/trailing NaNs before calculating the
        # fraction of missing data
        nan_indices = np.where(~np.isnan(aux_raw))[0]

        if nan_indices.size == 0:
            print(f"{t_ref}: no valid sea-level data")
            continue

        first_valid = nan_indices[0]
        last_valid = nan_indices[-1]

        # +1 because the last index is included
        aux_cut = aux_raw[
            first_valid:last_valid + 1
        ]

        # Fraction of NaNs in the actual analysis window
        nan_frac = (
            np.isnan(aux_cut).sum() / len(aux_cut)
        )

        if nan_frac > umbral_nan:
            print(
                f"{t_ref}: too many NaNs "
                f"({nan_frac:.1%})"
            )
            continue

        if len(aux_cut) < n_fft_welch:
            print(
                f"{t_ref}: not enough valid samples "
                f"for Welch periodogram"
            )
            continue

        # Interpolate only the remaining internal NaNs
        aux = (
            pd.Series(aux_cut)
            .interpolate(
                method="linear",
                limit_direction="both"
            )
            .to_numpy()
        )

        # ----------------------------------------------------
        # Welch periodogram
        # ----------------------------------------------------

        frequency, pwel = welch_periodogram(
            aux - np.mean(aux),
            dt,
            n_fft_welch,
            segment_length=n_fft_welch,
            overlap=0.5
        )

        # ----------------------------------------------------
        # Restrict spectrum to the valid period range
        # Tmin <= T <= Tmax
        # ----------------------------------------------------

        valid = (
            (frequency >= 1 / Tmax) &
            (frequency <= 1 / Tmin)
        )

        frequency = frequency[valid]
        pwel = pwel[valid]

        if len(frequency) == 0:
            print(
                f"{t_ref}: no frequencies inside "
                f"{Tmin}-{Tmax} s"
            )
            continue

        # ----------------------------------------------------
        # Spectral moments
        # ----------------------------------------------------

        m0_w = np.sum(pwel)
        m1_w = np.sum(
            pwel * frequency
        )
        m2_w = np.sum(
            pwel * frequency**2
        )

        # ----------------------------------------------------
        # Peak period
        # ----------------------------------------------------

        ind_peak = np.argmax(pwel)

        # ----------------------------------------------------
        # Wave parameters
        # ----------------------------------------------------

        Hm_w[n] = (
            np.sqrt(m0_w) * 4
        )

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

        tp_w[n] = (
            1 / frequency[ind_peak]
            if frequency[ind_peak] != 0
            else np.nan
        )

        # ----------------------------------------------------
        # Save result
        # ----------------------------------------------------

        result_df = pd.DataFrame({
            "TIME": [t_ref],
            "Hsig": [round(Hm_w[n], 8)],
            "Tp": [round(tp_w[n], 8)],
            "Tm1": [round(Tm1_w[n], 8)],
            "Tm2": [round(Tm2_w[n], 8)]
        })

        result_df["TIME"] = (
            result_df["TIME"]
            .dt.strftime("%Y-%m-%d %H:%M:%S")
        )

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

    print("\n=== Download and calculation finished!!! ===")
    print(f"Saved output file: {output_file}\n")


# ============================================================
# MAIN
# ============================================================

def main():

    try:
        station, start_date, end_date = ask_inputs()

    except Exception as e:
        print(f"\n Error en la entrada: {e}")
        return

    df = load_puertos_series(
        station,
        start_date,
        end_date
    )

    if df is None:
        return

    calculate_wave_params(
        df,
        start_date,
        end_date,
        station
    )

    print(
        "If you have problems with the data, "
        "check Puertos OPeNDAP:"
    )
    print(
        "https://opendap.puertos.es/thredds/catalog/catalog.html"
    )
    print(
        "If there is no available data for your domain of interest, "
        "you cannot use this module :("
    )
    print("You could always adapt the script to your own data")


if __name__ == "__main__":
    main()
