# downloads wind data and creates wind file required by swan for +60h
from ecmwfapi import ECMWFService
import xarray as xr
import yaml
import os
import sys
from datetime import datetime, timezone

CONFIG_FILE = "../../config/cases.yml"
OUTPUT_BASE = "../../cases"

def read_case_point(case_name):
    with open(CONFIG_FILE, "r") as f:
        cases = yaml.safe_load(f)

    if case_name not in cases:
        raise ValueError(f"Case '{case_name}' not found in {CONFIG_FILE}")

    point = cases[case_name]["boundary_point"]
    return float(point["lat"]), float(point["lon"])

def main():
    if len(sys.argv) < 6:
        print("Usage: python download_ecmwf_wind.py <case_name> <swan_case_name> <latitude> <longitude> <YYYYMMDD>")
        sys.exit(1)

    case_name = sys.argv[1]
    swan_case_name = sys.argv[2]
    latitude = float(sys.argv[3])
    longitude = float(sys.argv[4])
    today = datetime.strptime(sys.argv[5], "%Y%m%d").replace(tzinfo=timezone.utc)

    # Point defined in cases.yml
    config_lat, config_lon = read_case_point(case_name)

    print(f"Case: {case_name}")
    print(f"ECMWF point from cases.yml: {config_lat:.2f}, {config_lon:.2f}")

    # Check that the coordinates passed by the operational script agree
    if abs(latitude - config_lat) > 1e-6 or abs(longitude - config_lon) > 1e-6:
        print(
            f"WARNING: coordinates passed to the script "
            f"({latitude}, {longitude}) differ from cases.yml "
            f"({config_lat}, {config_lon})"
        )

    date_str = today.strftime("%Y%m%d")

    # Temporary ECMWF file
    tmp_file = f"/tmp/ecmwf_wind_{case_name}_{date_str}.nc"

    # SWAN output
    output_dir = f"{OUTPUT_BASE}/{case_name}/wind"
    output_dat = os.path.join(output_dir, f"wind_{swan_case_name}.dat")
    os.makedirs(output_dir, exist_ok=True)

    # --------------------------------------------------------
    # ECMWF
    # --------------------------------------------------------
    server = ECMWFService("mars")

    server.execute(
        {
            "class": "od",
            "date": date_str,
            "expver": "1",
            "levtype": "sfc",
            "param": "165.128/166.128",
            "step": "1/to/60/by/1",
            "stream": "oper",
            "time": "00",
            "type": "fc",
            "format": "netcdf",
            "area": f"{config_lat}/{config_lon}/{config_lat}/{config_lon}",
            "grid": "0.1/0.1"
        },
        tmp_file
    )

    # --------------------------------------------------------
    # Read ECMWF
    # --------------------------------------------------------
    ds = xr.open_dataset(tmp_file)

    # Nearest ECMWF grid point
    point = ds.sel(
        latitude=config_lat,
        longitude=config_lon,
        method="nearest"
    )

    u = point["u10"].values
    v = point["v10"].values

    ecmwf_lat = float(point.latitude)
    ecmwf_lon = float(point.longitude)

    print(f"ECMWF grid point: {ecmwf_lat:.2f}, {ecmwf_lon:.2f}")
    print(f"Forecast hours: {len(u)}")

    # --------------------------------------------------------
    # Write SWAN wind file
    # --------------------------------------------------------
    with open(output_dat, "w") as f:
        for ux, vy in zip(u, v):
            f.write(f"{ux:.6f} {ux:.6f} {ux:.6f} {ux:.6f}\n")
            f.write(f"{vy:.6f} {vy:.6f} {vy:.6f} {vy:.6f}\n")

    print(f"SWAN wind file generated: {output_dat}")

    os.remove(tmp_file)

if __name__ == "__main__":
    main()
