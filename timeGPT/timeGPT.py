#timegpt for operational forecasting system
# by @laloyo 
#last modifed: 07/09/2026
##############^w^################
#import key from .env
from dotenv import load_dotenv
load_dotenv()

from nixtla import NixtlaClient
nixtla_client = NixtlaClient()
#validate key is okkkk
nixtla_client.validate_api_key()

# import rest libraries
import pandas as pd
import sys
import os
from datetime import date, datetime, timezone, timedelta

# --------------------------------------------------
# Arguments
# --------------------------------------------------

if len(sys.argv) < 4:
    print("Usage:")
    print("    python timeGPT.py <case_name> <variable>")
    print("")
    print("Available variables:")
    print("    Hsig")
    print("    Tp")
    print("    Tm1")
    print("    Tm2")
    sys.exit(1)

case_name = sys.argv[1]
target_var = sys.argv[2]
future_file_path=sys.argv[3] # swan forecast

#Variables that can be predicted
allowed_vars = ['Hsig', 'Tp', 'Tm1', 'Tm2']

if target_var not in allowed_vars:
    print(f"Error: '{target_var}' is not a valid prediction variable.")
    print(f"Choose one of: {', '.join(allowed_vars)}")
    sys.exit(1)

# --------------------------------------------------
# Input data
# --------------------------------------------------

print("remember to define the path to the combined data in the script timeGPT.py")
print("all the required preprocessing steps are explained in ./timeGPT/pre/README ")

# Read combined data:
#   Time          -> datetime
#   Hsig_swan     -> exogenous variable
#   RTpeak_swan   -> exogenous variable
#   Dir_swan      -> exogenous variable
#   Hsig/Tp/Tm1/Tm2 -> target variable

path_combined_data = f"./combine/{case_name}/Hsig_exog_vars_swan-calcMareograf.csv"
#df = pd.read_csv(path_combined_data)
df = pd.read_csv(path_combined_data, skiprows=1 ,sep=" ", names=["Time", "Exogenous1", "Exogenous2", "Exogenous3", "Hsig", "Tp", "Tm1", "Tm2"])

print(df.head())
# Rename Time to ds, as required by TimeGPT
df = df.rename(columns={'Time': 'ds'})

# Convert time to datetime
df['ds'] = pd.to_datetime(df['ds'])

# Check that the requested variable exists
if target_var not in df.columns:
    print(f"Error: variable '{target_var}' not found in the input file.")
    print(f"Available columns: {list(df.columns)}")
    sys.exit(1)

# Set selected variable as target
df = df.rename(columns={target_var: 'y'})

# Keep only the columns needed by TimeGPT
df = df[
    [
        'ds',
        'Exogenous1', #Hsig_swan
        'Exogenous2', #RTpeak_swan
        'Exogenous3', #Dir_swan
        'y'
    ]
]

print(f"\nPrediction variable: {target_var}")
print("\nData:")
print(df.tail())
# --------------------------------------------------
# read future
# --------------------^_^------------------------------

# read
df_future = pd.read_csv(future_file_path, sep=r'\s+', skiprows=7, header=None,
                     names=['ds', 'Xp', 'Yp', 'Depth', 'Exogenous1', 'Tm02_swan', 'Exogenous2', 'Exogenous3'], dtype={"ds": str}) #exos: hisg, rtpeak,dir
df_future = df_future[['ds', 'Exogenous1', 'Exogenous2', 'Exogenous3']]
df_future['ds'] = df_future['ds'].str.replace(r'\.', '', regex=True)  # Remove decimal
df_future['ds'] = pd.to_datetime(df_future['ds'], format='%Y%m%d%H%M%S')  # Convert to datetime
df_future=df_future.iloc[1:, :] #primer valor de simulación siempre está mal
print(df_future.head())
print(df_future.tail())

# we see how many swan hours were simulated in order to predict the same with timegpt
h = len(df_future)

#fcst with timeGPT
timegpt_fcst_ex_vars_df = nixtla_client.forecast(df=df, X_df=df_future, h=h, level=[80, 90], freq="1h")
#save 
today = datetime.now(timezone.utc)
today_str = today.strftime("%Y%m%d")
print(today_str)
time_dir = today.strftime("%Y%m")
save_dir = f"./prediction/{case_name}/{time_dir}/" # we can change this to be more for any user with a path variable
os.makedirs(save_dir, exist_ok=True)
output_file=os.path.join(save_dir, f"Hsig_swan{today_str}.csv")
print(output_file)
# modify date to today, as we treaked (trampa) timeGPT
n_rows = timegpt_fcst_ex_vars_df.shape[0]

today_utc_midnight = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
new_dates = pd.date_range(start=today_utc_midnight, periods=n_rows, freq='h')
timegpt_fcst_ex_vars_df['ds'] = new_dates

print(timegpt_fcst_ex_vars_df.head())
# and now we can SAVE timeGPT's prediction
timegpt_fcst_ex_vars_df.to_csv(output_file, sep='\t', index=False)

