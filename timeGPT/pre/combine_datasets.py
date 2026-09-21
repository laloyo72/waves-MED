# code to combine mareograf and exogenous vars from PdE
# 03/07/2026 by @laloyo
# ------------------------------------------------------ #
import os
import pandas as pd
import numpy as np
import sys
from datetime import datetime

print("you have to select the files you want to combine, open the script!!")

# PATHHHHHHHHHHHHHHH to files:

# remeber to do a long swan run to train timeGPT module
#swan_long_sim_file="/home/laloyo/waves-iber/cases/alcudia/output/table_mareograph_cat1_2025.txt"
#merged_file="../combine/alcudia/Hsig_exog_vars_swan-calcMareograf.csv"
#mareograf_file="../DATA//mareograf/calculated/alcudia/wave_parameters_20250101_20260101.csv"


swan_long_sim_file="/home/laloyo/waves-MED/cases/bilbo/output/tableP_cat0_F3_20250101_20260101.txt"
mareograf_file="../DATA//mareograf/calculated/bilbo/wave_parameters_bilbo_20250101_20260101.csv"

merged_file="../combine/bilbo/Hsig_exog_vars_swan-calcMareograf.csv"
os.makedirs(os.path.dirname(merged_file), exist_ok=True)
def read_mareograf_calc(file_simar):
    df = pd.read_csv(
        file_simar,
        sep="\t",
        skiprows=1,
        names=["Time", "Hsig", "Tp", "Tm1", "Tm2"]
    )
    
    df["Time"] = pd.to_datetime(df["Time"], format="%Y-%m-%d %H:%M:%S")
    
    # Replace 21.33 with NaN
    df = df.replace(21.333333333333332, np.nan)
    
    df = df.set_index("Time") # para interpolar con time
    # Interpolate numeric columns
    num_cols = ["Hsig", "Tp", "Tm1", "Tm2"]
    df[num_cols] = df[num_cols].interpolate(method="time")

    df = df.reset_index()

    # Round to 3 decimals
    df[num_cols] = df[num_cols].round(3)
    
    return df
def read_swan(file_swan):
    df = pd.read_csv(file_swan, sep=r'\s+', skiprows=7, header=None, 
                     names=['Time', 'Xp', 'Yp', 'Depth', 'Hsig_swan', 'Tm02_swan', 'RTpeak_swan', 'Dir_swan'], dtype={"Time": str})
    df = df[['Time', 'Hsig_swan', 'RTpeak_swan', 'Dir_swan']]  
    df['Time'] = df['Time'].str.replace(r'\.', '', regex=True)  # Remove decimal
    df['Time'] = pd.to_datetime(df['Time'], format='%Y%m%d%H%M%S')  # Convert to datetime
    return df

def merge_csv(df1, df2, output_file):
    
    # Merge using nearest time matching
    df_merged = pd.merge_asof(df2.sort_values("Time"), df1.sort_values("Time"), on="Time", direction="nearest")
    
    # Save to new CSV
    df_merged.to_csv(output_file, sep=" ", index=False)
    print(f"Merged file saved as {output_file}")

# Load first CSV (Fecha (GMT) and Hsig)
df_mareograf = read_mareograf_calc(mareograf_file)
#df_simar = read_simar(simar_file)
# Load second CSV (Keeping its time format)
df_swan = read_swan(swan_long_sim_file)

merge_csv(df_mareograf, df_swan, merged_file)
#print(df_swan.head())

