# simple script to plot some timeseries, and validate the model's results
import pandas as pd
import matplotlib.pyplot as plt

# Define file paths
swan_case= "../../cases/tarragona/output/tableP_cat0_F3_20260101_20260901.txt"
swan_cased = "../../cases/tarragona/output/tablePd_cat0_F3_20260101_20260901.txt"
mareograf_calc = "../../timeGPT/DATA/mareograf/calculated/tarragona/wave_parameters_tarragona_20260101_20260901.csv"

# Function to read SOCIB data
def read_socib(file_path):
    df = pd.read_csv(file_path, sep=r'\s+', skiprows=1, header=None, names=['Time', 'Hsig', 'RTpeak', 'Tm02' , 'Dir'], dtype={"Time": str})
    df['Time'] = df['Time'].str.replace(r'\.', '', regex=True)  # Remove decimal
    df['Time'] = pd.to_datetime(df['Time'], format='%Y%m%d%H%M%S')  # Convert to datetime
    return df
# read downloaded tide_gauge
def read_mareograf_puertos(file_path):
    df = pd.read_csv(file_path, sep=r'\s+', skiprows=1, header=None, names=['Time', 'Hsig', 'Tm02' , 'Hmax'], dtype={"Time": str})
    df['Time'] = df['Time'].str.replace(r'\.', '', regex=True)  # Remove decimal
    df['Time'] = pd.to_datetime(df['Time'], format='%Y%m%d%H%M%S')  # Convert to datetime
    return df

# read SWAN output
def read_swan(file_path):
    df = pd.read_csv(file_path, sep=r'\s+', skiprows=7, header=None, 
                     names=['Time', 'Xp', 'Yp', 'Depth', 'Hsig', 'Tm02', 'RTpeak', 'Dir'], dtype={"Time": str})
    df = df[['Time', 'Hsig', 'RTpeak', 'Tm02', 'Dir']]  
    df['Time'] = df['Time'].str.replace(r'\.', '', regex=True)  # Remove decimal
    df['Time'] = pd.to_datetime(df['Time'], format='%Y%m%d%H%M%S')  # Convert to datetime
    return df
# read SWAN wind output 
def read_swan_wind(file_path): 
    df = pd.read_csv(file_path, sep=r'\s+', skiprows=7, header=None,
                     names=['Time', 'Xp', 'Yp', 'Depth', 'Hsig', 'Tm02', 'Dir', 'wx', 'wy'], dtype={"Time": str})
    df = df[['Time', 'Hsig', 'Tm02', 'Dir']]
    df['Time'] = df['Time'].str.replace(r'\.', '', regex=True)  # Remove decimal
    df['Time'] = pd.to_datetime(df['Time'], format='%Y%m%d%H%M%S')  # Convert to datetime
    return df 
# calculated tide gauge
def read_mareograf_calc(file_simar):
    # Read the second file skipping the first line
    df = pd.read_csv(file_simar, sep="\t", skiprows=1, names=["Time", "Hsig", "Tp", "Tm1", "Tm2"])
    df["Time"] = pd.to_datetime(df["Time"], format="%Y-%m-%d %H:%M:%S")
    #print("Second file time format:")
    #print(df["Time"].head())
    return df

# Read datasets
df_swan = read_swan(swan_case)
df_swand = read_swan(swan_cased)
df_mareograf = read_mareograf_calc(mareograf_calc)

# dates
start_date = pd.to_datetime("2026-01-01")
end_date = pd.to_datetime("2026-09-01")
print(df_swan.head())
print(df_swand.head())
print(df_mareograf.head())

# Plot Wave Height (Hsig) Comparison for the filtered day
plt.figure(figsize=(15, 10))
plt.plot(df_swan['Time'], df_swan['Hsig'], label='SWAN', marker=' ')
plt.plot(df_swand['Time'], df_swand['Hsig'], label='SWAN-inside-port', marker=' ') 
plt.plot(df_mareograf['Time'], df_mareograf['Hsig'], label='Mareógrafo', marker=' ')

plt.xlabel("Tiempo", fontsize=16, weight='bold')
#plt.ylabel("Dir ()", fontsize=14)
#plt.ylabel("Dir (\N{DEGREE SIGN})", fontsize=16, weight='bold')
#plt.ylabel("Tp(s)", fontsize=16, weight='bold')
plt.ylabel("Hs(m)", fontsize=16, weight='bold')
#plt.title("Altura Significante: Observación vs Modelo", fontsize=20, weight='bold')
plt.xlim(start_date, end_date)
#plt.ylim(0,1)
plt.legend(fontsize=16)
plt.xticks(rotation=20, fontsize=16) 
plt.yticks(fontsize=16)
plt.grid()
#plt.savefig("../../cases/alcudia/figures/Hsig_SOCIBvsSWANvsSWANwindVSwtcap_20230101-20231231.png")
plt.show()
