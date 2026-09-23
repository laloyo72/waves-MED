import pandas as pd
import matplotlib.pyplot as plt
import os
import sys
from datetime import date, datetime, timedelta


# ============================================================
# CASE
# ============================================================

if len(sys.argv) != 3:
    print("Usage: python validate_op.py <case>")
    sys.exit(1)

case_name = sys.argv[1].lower()
swan_case = sys.argv[2].lower()
print(f"Validating case: {case_name}, {swan_case}")


# ============================================================
# DATES
# ============================================================

today = date.today()
# today = datetime(2025, 5, 25).date()
today_str = today.strftime("%Y%m%d")

yesterday = today - timedelta(days=1)
yesterday_str = yesterday.strftime("%Y%m%d")

year = yesterday.year
month = yesterday.month
day = yesterday.day

print("yesterday was:")
print(year, month, day)


# ============================================================
# PATHS
# ============================================================

case_path = f"../../cases/{case_name}"
mareograf_calc = f"{case_path}/validation/mareograf/wave_parameters{yesterday_str}.txt"
base_path = f"{case_path}/output/{year}{month:02d}/"
file_suffix = f"{yesterday_str}_{today_str}.txt"


# ============================================================
# SWAN FILES
# ============================================================

file_patterns = {
    "F0": base_path + f"tableP_{swan_case}_F0_{file_suffix}",
    "F1": base_path + f"tableP_{swan_case}_F1_{file_suffix}",
    "F2": base_path + f"tableP_{swan_case}_F2_{file_suffix}",
    "F3": base_path + f"tableP_{swan_case}_F3_{file_suffix}"
}

available_files = {
    name: path for name, path in file_patterns.items()
    if os.path.isfile(path)
}

if not available_files:
    print("ERROR: No SWAN output files found for yesterday.")
    sys.exit(0)

print("\nAvailable SWAN files:")
for name, path in available_files.items():
    print(f"  {name}: {path}")



# ============================================================
# READING FUNCTIONS
# ============================================================

def read_mareograf_wave_parameters(file_path):
    df = pd.read_csv(file_path, sep='\t')
    df = df.rename(columns=str.strip)
    df['Time'] = pd.to_datetime(df['TIME'], format='%Y-%m-%d %H:%M:%S')
    return df


def read_swan(file_path):
    df = pd.read_csv(
        file_path,
        sep=r'\s+',
        skiprows=7,
        header=None,
        names=['Time', 'Xp', 'Yp', 'Depth', 'Hsig', 'Tm02', 'RTpeak', 'Dir'],
        dtype={"Time": str}
    )
    df = df[['Time', 'Hsig', 'RTpeak', 'Tm02', 'Dir']]
    df['Time'] = df['Time'].str.replace(r'\.', '', regex=True)
    df['Time'] = pd.to_datetime(df['Time'], format='%Y%m%d%H%M%S')
    return df


# ============================================================
# READ DATA
# ============================================================

swan_data = {}

for name, path in available_files.items():
    print(f"Reading {name}...")
    swan_data[name] = read_swan(path)

print("Reading tide gauge...")
df_mareograf = read_mareograf_wave_parameters(mareograf_calc)


# ============================================================
# FILTER 24 HOURS
# ============================================================

start_time = datetime.combine(yesterday, datetime.min.time())
end_time = datetime.combine(today, datetime.min.time())

def filter_24h(df):
    return df[(df['Time'] >= start_time) & (df['Time'] < end_time)]

swan_data_day = {name: filter_24h(df) for name, df in swan_data.items()}
df_mareograf_day = filter_24h(df_mareograf)


# ============================================================
# PLOT Hsig
# ============================================================

plt.figure(figsize=(15, 10))

plt.plot(df_mareograf_day['Time'], df_mareograf_day['Hsig'], label='Mareógrafo', linestyle='dashed')

for name, df in swan_data_day.items():
    plt.plot(df['Time'], df['Hsig'], label=f'SWAN - {name}')

plt.xlabel("Time", fontsize=16, weight='bold')
plt.ylabel("Hs (m)", fontsize=16, weight='bold')
plt.title("Significant Wave Height: Observation vs Numerical Model", fontsize=20, weight='bold')
plt.legend(fontsize=16)
plt.xticks(rotation=20, fontsize=16)
plt.yticks(fontsize=16)
plt.grid()

fig_dir = os.path.join(case_path, "figures/compare_op")
os.makedirs(fig_dir, exist_ok=True)

fig_path = os.path.join(fig_dir, f"Hsig_mareograf_calCvsSWAN_{yesterday_str}.png")
plt.savefig(fig_path)
print(f"Saved: {fig_path}")


# ============================================================
# PLOT RTpeak
# ============================================================

plt.figure(figsize=(12, 6))

plt.plot(df_mareograf_day['Time'], df_mareograf_day['Tp'], label='Mareógrafo', linestyle='dashed')

for name, df in swan_data_day.items():
    plt.plot(df['Time'], df['RTpeak'], label=f'SWAN - {name}')

plt.xlabel("Time", fontsize=16, weight='bold')
plt.ylabel("Peak period (s)", fontsize=16, weight='bold')
plt.title("Peak period: Observation vs Numerical Model", fontsize=20, weight='bold')
plt.legend(fontsize=16)
plt.xticks(rotation=20, fontsize=16)
plt.yticks(fontsize=16)
plt.grid()

fig_path = os.path.join(fig_dir, f"RTpeak_mareograf_calCvsSWAN_{yesterday_str}.png")
plt.savefig(fig_path)
print(f"Saved: {fig_path}")

plt.show()
