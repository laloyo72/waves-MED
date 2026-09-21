# we need to check if for the long combined data there is some date missing.
# timeGPT needs all timestamps, we cannot miss any
import pandas as pd
import numpy as np
import sys
from datetime import datetime
# -------------------
# read combined dataset
# -------------------
merged_file="../combine/tarragona/Hsig_exog_vars_swan-calcMareograf.csv"

df = pd.read_csv(merged_file, skiprows=1 ,sep=" ", names=["Time", "Hsig_swan", "RTpeak_swan", "Dir_swan", "Hsig", "Tp", "Tm1", "Tm2"])
print(df.tail())

df['Time'] = pd.to_datetime(df['Time'])

print(df.tail())
# --------------------------------------------------
# Check missing timestamps
# --------------------------------------------------

# Convert Time to datetime
#df['ds'] = pd.to_datetime(df['Time'])

# Sort by time
df = df.sort_values('Time').reset_index(drop=True)

# Expected hourly timestamps from first to last date
expected_dates = pd.date_range(
    start=df['Time'].min(),
    end=df['Time'].max(),
    freq='1h'
)

# Find missing timestamps
missing_dates = expected_dates.difference(df['Time'])

if len(missing_dates) > 0:
    print("\nWARNING: Missing timestamps found!")
    print(f"Number of missing timestamps: {len(missing_dates)}")
    print("\nMissing timestamps:")

    for date in missing_dates:
        print(date)

    sys.exit(1)

else:
    print("\nNo missing timestamps found.")

