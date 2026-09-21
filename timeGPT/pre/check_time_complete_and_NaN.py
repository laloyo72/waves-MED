# we need to check if for the long combined data there is some date missing.
# timeGPT needs all timestamps, we cannot miss any
import pandas as pd
import numpy as np
import sys
from datetime import datetime

# -------------------
# read combined dataset
# -------------------
#merged_file="../combine/tarragona/Hsig_exog_vars_swan-calcMareograf_mal.csv"
merged_file = "../combine/bilbo/Hsig_exog_vars_swan-calcMareograf.csv"

df = pd.read_csv(
    merged_file,
    skiprows=1,
    sep=" ",
    names=["Time", "Hsig_swan", "RTpeak_swan", "Dir_swan", "Hsig", "Tp", "Tm1", "Tm2"]
)

df['Time'] = pd.to_datetime(df['Time'])

# Sort by time
df = df.sort_values('Time').reset_index(drop=True)

# Keep track of whether any problem was found
problems_found = False


# --------------------------------------------------
# 1. Check missing timestamps
# --------------------------------------------------

expected_dates = pd.date_range(
    start=df['Time'].min(),
    end=df['Time'].max(),
    freq='1h'
)

missing_dates = expected_dates.difference(df['Time'])

if len(missing_dates) > 0:
    problems_found = True

    print("\nWARNING: Missing timestamps found!")
    print(f"Number of missing timestamps: {len(missing_dates)}")
    print("\nMissing timestamps:")

    for date in missing_dates:
        print(date)

else:
    print("\nNo missing timestamps found.")


# --------------------------------------------------
# 2. Check NaN values
# --------------------------------------------------

nan_rows = df[df.isna().any(axis=1)]

if len(nan_rows) > 0:
    problems_found = True

    print("\nWARNING: NaN values found!")
    print(f"Number of rows containing NaN: {len(nan_rows)}")
    print("\nRows with NaN values:")
    print(nan_rows.to_string(index=False))

else:
    print("\nNo NaN values found.")


# --------------------------------------------------
# 3. Check suspicious Tp value
# --------------------------------------------------

bad_tp = np.isclose(df['Tp'], 21.333)
#print(df['Tp'].tail(20))
#print(df['Tp'].dtype)

if bad_tp.any():
    problems_found = True

    bad_tp_rows = df[bad_tp]

    print("\nWARNING: Suspicious Tp value found!")
    print(f"Number of rows with Tp ≈ 21.3333: {len(bad_tp_rows)}")
    print("\nRows with suspicious Tp:")
    print(bad_tp_rows.to_string(index=False))

else:
    print("\nNo suspicious Tp values found.")


# --------------------------------------------------
# Final result
# --------------------------------------------------

print("\n" + "-" * 50)

if problems_found:
    print("CHECK FAILED: Problems were found in the file.")
    sys.exit(1)
else:
    print("CHECK PASSED: No problems found.")
