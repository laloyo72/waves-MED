# last modified 21/09/26 : generalizing with config/cases.yml file
import os
import xarray as xr
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
import yaml

# ============================================================
# CASES CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[2]
CASES_FILE = ROOT / "config" / "cases.yml"

def load_cases():
    with open(CASES_FILE, "r") as f:
        return yaml.safe_load(f)


def ask_inputs():
    cases = load_cases()

    print("\n=== SIMAR boundary conditions ===\n")
    print("Available cases:")

    for case in cases:
        print(f" - {case}")

    case_name = input("\nSelect case: ").strip().lower()

    if case_name not in cases:
        raise ValueError(f"'{case_name}' is not in cases.yaml.")

    # Get boundary point from cases.yaml
    boundary_point = cases[case_name].get("boundary_point")

    if boundary_point is None:
        raise ValueError(
            f"No boundary_point configured for case '{case_name}'."
        )

    lat = boundary_point["lat"]
    lon = boundary_point["lon"]

    print(f"\nSelected case: {case_name}")
    print(f"Boundary point: {lat}, {lon}")

    start_str = input("\nStart date (YYYY-MM-DD): ").strip()
    end_str = input("End date   (YYYY-MM-DD): ").strip()

    start_date = datetime.strptime(
        start_str, "%Y-%m-%d"
    ).replace(tzinfo=timezone.utc)

    end_date = datetime.strptime(
        end_str, "%Y-%m-%d"
    ).replace(tzinfo=timezone.utc)

    return case_name, lat, lon, start_date, end_date


# ============================================================
# INPUTS
# ============================================================

case_name, lat, lon, start_date, end_date = ask_inputs()


# ============================================================
# OUTPUT
# ============================================================

start_str = start_date.strftime("%Y%m%d")
end_str = end_date.strftime("%Y%m%d")

output_file = (
    ROOT / "cases" / case_name / "input" /
    f"TPAR_simar_{start_str}-{end_str}_{lat}_{lon}.txt"
)

output_file.parent.mkdir(parents=True, exist_ok=True)

print(f"\nOutput file:")
print(output_file)

df_all = pd.DataFrame() #acumulamos data

current_date = start_date
while current_date <= end_date:
    try:
        current_date_str = current_date.strftime("%Y%m%d")  # Format date as YYYYMMDD
        year, month = current_date.year, current_date.month

        # Generate the URL for the specific day
        url=f"http://opendap.puertos.es/thredds/dodsC/wave_regional_aib/{year}/{month:02d}/HW-{current_date_str}-HC.nc"
        #url = f"http://opendap.puertos.es/thredds/dodsC/wave_regional_aib/{year}/{month:02d}/HW-{current_date_str}-HC.nc"
        print(f"Downloading from: {url}")

        # Open the dataset
        ds = xr.open_dataset(url)

        # Select relevant variables (Hs, RTpeak, peak wave direction)
        vars = ds[["VHM0", "VTPK", "VMDR"]]
        point_data = vars.sel(latitude=lat, longitude=lon, method="nearest")

        # Convert to DataFrame and format time
        df = point_data.to_dataframe().reset_index()
        df["Timestamp"] = df["time"].dt.strftime("%Y%m%d.%H%M%S")
        df["Desv_dir"] = 20. # assuming directional spread is always 20...
        df = df[["Timestamp", "VHM0", "VTPK", "VMDR", "Desv_dir"]]
        #df = df[["Timestamp", "VHM0", "VTPK", "VPED"]]

        # Accumulate data
        df_all = pd.concat([df_all, df], ignore_index=True)

    except Exception as e:
        print(f"Error downloading or saving {current_date_str}: {e}")

    # Move to the next day
    current_date += timedelta(days=1)

# Save all data into a single file
if not df_all.empty:
    with open(output_file, "a") as f:
                    f.write("TPAR\n")
                    df_all.to_csv(f, sep=" ", index=False, header=False, float_format="%.3f")
    #df_all.to_csv(output_file, sep='\t', index=False)
    print(f"All data saved in {output_file}")
else:
    print("No data available for the specified date range.")

