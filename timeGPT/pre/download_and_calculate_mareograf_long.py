# we are trying to adapt joan's matlab code to calculate Hsig and Tp 
# from mareograf series of Puertos
# generalized & interactive version for operational use
# by @laloyo + copi 23/06/26
###################^w^####################
import numpy as np
import pandas as pd
import scipy.fftpack as fft
import xarray as xr
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
import yaml


# ============================
# CASES CONFIGURATION
# ============================

ROOT = Path(__file__).resolve().parents[2]
CASES_FILE = ROOT / "config" / "cases.yml"

BASE_OPENDAP = "http://opendap.puertos.es/thredds/dodsC"


def load_cases():
    """Load case configuration from cases.yml."""
    with open(CASES_FILE, "r") as f:
        return yaml.safe_load(f)


def ask_inputs():
    print("\n=== Available Tide Gauges from PdE → Hsig/Tp (TimeGPT helper) ===\n")
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
            df_day = ds[["TIME", "SLEV"]].to_dataframe().reset_index()
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
        print("\n   Sin datos de mareógrafo no puedes usar el módulo TimeGPT :(\n")
        return None

    df = pd.DataFrame({"TIME": time_list, "SLEV": slev_list})
    df["TIME"] = pd.to_datetime(df["TIME"], utc=True)
    return df


def interpolate_slev(df):
    nan_indices = df["SLEV"].isna()

    # parámetros
    umbral_nan = 0.1      # 10% NaNs allowed in each block
    intervalo_muestras = 960  # nº de muestras por bloque (ajusta a tu sampling real)

    df["SLEV_interp"] = df["SLEV"].copy()

    for i in range(0, len(df) - intervalo_muestras, intervalo_muestras):
        indices_intervalo = np.arange(i, i + intervalo_muestras)

        num_nans_intervalo = nan_indices.iloc[indices_intervalo].sum()
        num_datos_intervalo = len(indices_intervalo)

        if num_nans_intervalo / num_datos_intervalo <= umbral_nan:
            valid_data = df.loc[indices_intervalo, "SLEV"].dropna()
            if len(valid_data) > 1:
                df.loc[indices_intervalo, "SLEV_interp"] = (
                    df.loc[indices_intervalo, "SLEV"]
                    .interpolate(method="linear", limit_direction="both")
                )

    return df


def calculate_wave_params(df, start_date, end_date, station):
    SL_interpolado = df["SLEV_interp"].values
    time = df["TIME"].values

    # time vector for simulation
    timeVec = pd.date_range(start=start_date, end=end_date, freq="1h")

    # FFT params
    n_fft = 1024 // 2
    Tmin = 1
    Tmax = 20
    dt = 0.5
    n_fmax = int(n_fft * dt / Tmin)
    n_fmin = int(np.floor(n_fft * dt / Tmax))

    Hm  = np.zeros(len(timeVec))
    Tm1 = np.zeros(len(timeVec))
    Tm2 = np.zeros(len(timeVec))
    tp  = np.zeros(len(timeVec))
    spt_news = [None] * len(timeVec)
    spt_filt = [None] * len(timeVec)

    # YYYYMMDD for date writting
    start = start_date.strftime("%Y%m%d")
    end = end_date.strftime("%Y%m%d")

    outdir = f"../DATA/mareograf/calculated/{station}"
    os.makedirs(outdir, exist_ok=True)
    output_file = os.path.join(outdir, f"wave_parameters_{station}_{start}_{end}.csv")

    # si existe de antes, lo borramos para no mezclar runs
    if os.path.exists(output_file):
        os.remove(output_file)

    for n, t_ref in enumerate(timeVec):
        t_ref_np = np.datetime64(t_ref.replace(tzinfo=None))
        ind = np.argmin(np.abs(time - t_ref_np))

        if ind >= len(time) - n_fft + 1:
            continue

        aux = SL_interpolado[ind:ind + n_fft]

        new_fft = fft.fft(aux - np.mean(aux), n_fft)
        new_spt = np.abs(new_fft) ** 2
        new_spt = 2 * new_spt / (n_fft ** 2)

        new_spt[:n_fmin] = 0
        new_spt[n_fmax:] = 0

        new_freq = np.arange(len(new_spt)) / (n_fft * dt)
        new_freq = new_freq[:n_fmax]
        new_spt  = new_spt[:n_fmax]

        spt_news[n] = new_spt
        spt_filt[n] = new_spt * (1 - (1 / (1 + ((new_freq / (2 / Tmax)) ** 2) ** 2)))

        new_period = 1 / new_freq

        m0 = np.sum(spt_filt[n])
        m1 = np.sum(spt_filt[n] * new_freq)
        m2 = np.sum(spt_filt[n] * (new_freq ** 2))

        ind2 = np.argmax(spt_filt[n])

        Hm[n]  = np.sqrt(m0) * 4
        Tm1[n] = m0 / m1
        Tm2[n] = np.sqrt(m0 / m2)
        tp[n]  = new_period[ind2]

        result_df = pd.DataFrame({
            "TIME": [t_ref],
            "Hsig": [Hm[n]],
            "Tp":   [tp[n]],
            "Tm1":  [Tm1[n]],
            "Tm2":  [Tm2[n]],
        })
        result_df["TIME"] = result_df["TIME"].dt.strftime("%Y-%m-%d %H:%M:%S")

        result_df.to_csv(
            output_file,
            sep="\t",
            index=False,
            mode="a",
            header=not os.path.exists(output_file),
        )

        print(f"Results saved for {t_ref} in {output_file}")

    print("\n=== Download and calculation finishedd!!! ===")
    print(f"Saved output file: {output_file}\n")


def main():
    try:
        station, start_date, end_date = ask_inputs()
    except Exception as e:
        print(f"\n Error en la entrada: {e}")
        return

    df = load_puertos_series(station, start_date, end_date)
    if df is None:
        return

    df = interpolate_slev(df)
    calculate_wave_params(df, start_date, end_date, station)

    print("If you have problems with the data, check Puertos OPeNDAP:")
    print("https://opendap.puertos.es/thredds/catalog/catalog.html")
    print("If there is no available data for your domain of interest, you cannot use this module :(\n")
    print("You could always adapt the script to your own data")


if __name__ == "__main__":
    main()

