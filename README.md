# HRES operational system for Wave Forecasting
This system forecasts +60h of wave conditions around the Mediterranean Iberian Peninsula. It focuses on Palma de Mallorca's bay/port, but it can be adapted to any location within the Mediterranean Iberian Peninsula
## Requirements
Before running the system, you need to set up a few things:

### 1. SWAN Model
You need to have SWAN (Simulating Waves Nearshore) compiled with NetCDF support. You can follow the instructions in the [Implementation Manual](https://swanmodel.sourceforge.io/download/zip/swanimp.pdf) to download and compile SWAN.

### 2. Python Virtual Environment
A Python virtual environment is recommended for managing dependencies. You can create one and install the necessary packages from the `requirements.txt` file:

```bash
python3 -m venv waves-MED # you could call waves-MED virtual environment as you wanted and modify its source in the  main bash script
source waves-MED/bin/activate  # linux
pip install -r requirements.txt
```
### 4. Create a Nixtla Account (if model adjustment with timeGPT is wanted)
If you do not want to adjust the model's output with timeGPT just comment the line that executes `timeGPT.py` in the bash script.
Otherwise, go to [nixtla dashboard](dashboard.nixtla.io) and create an account. Once there, create an API key and save it in a `.env` file in the timeGPT folder. You can follow the instructions provided in section 2b of [Nixtla repo api-key set-up](https://nixtlaverse.nixtla.io/nixtla/docs/getting-started/setting_up_your_api_key.html)
```bash
vi .env
```
and write NIXTLA_API_KEY=your_api_key
## Project Overview
Here's a tree of the project folder structure:
```
waves-MED
│   automate_forecast_allINPUTfiles_timeGPT_plot.sh
│
└───cases
│   │
│   └───palma
│       │   README
│       │   input_ca00.swn
│       │   swan.exe
│       │   swaninit
│       │   swanrun
│       │
│       └───bathy
│       │       │    bottom_ca00_HRES_matrix.dat 
│       │       │    ...
│
└───DATA
│   │
│   └───bathy
│       │   bathy_iberian_LR.nc
│   │
│   └───coastline
│      │
│       └───Europe_coastline_2020_OSM
│           │   Europe_coastline_2020_OSM.shp
│           │   ...
│ 
└───scripts
│   │
│   └───bathy
│       │   download_and_interp_EMODNET_withcoastline_angle.py
│       │   download_bathy_gebco.py
│       │   plot_bathy_matrix.py
│   │
│   └───opendap
│       │   save_simar_point_to_TPAR.py
│       │   save_simar_point_to_TPAR_year.py
│   │
│   └───output
│       │   check_matlab.py
│       |   ...
│   │
│   └───plots
│       │   validate.py
│
└───start
│   │   input_ca00.swn
│   │   README
│   │   swan.exe  
│   │   swanrun
│  
└───timeGPT
│   │   timeGPT.py
│   │
│   └───combine
│       │   ...
│   │
│   └───DATA
│       │   ...
│   │
│   └───pre
│       │   check_time_complete.py
│       │   combine_datasets.py
│       │   download_and_calculate_mareograf_long.py
│   │
│   └───prediction
│       │   ...
│   .gitignore
│   README.md
│   requirements.txt  

```
- **`automate_forecast_allINPUTfiles_timeGPT_plot.sh`**: This file executes the operational system. Modify for your personal cases.
- **`/cases/`**: This directory holds the configuration files for various locations. Currently, there is a test case for Palma. However, you could configure new ones.
    - **`/palma/`**: The folder contains all the necessary files to run SWAN for Palma de Mallorca's bay, including:
        - **`/bathy/`**:
            - Bathymetry data (`bottom_ca00_HRES.dat`, etc.)
        - Input configuration files for SWAN (`input_caxx.swn`, etc.). The input_ca00.swn is the one configured to work operationally. Read the README to see the differences between input_caxx.swn.
        - Scripts to run SWAN (`swanrun`, etc.). When compiling swan in your computer you will need to cp the swanrun and swan.exe to each case you want to run. In this case I modified swanrun so that it uses 28cores. You will need to get them by compiling SWAN in your computer.

- **`/DATA/`**: Stores all data related to the simulations, including coastline data and bathymetry data.

- **`/scripts/`**: Contains Python scripts used for different tasks within the project. For example:
    - **`/bathy/`**:
        -  `download_and_interp_EMODNET_withcoastline_angle.py`:  Interpolates general bathymetry of Iberian Peninsula to local domain and creates the file needed to run SWAN in the region of interest, specified by input_caxx.swn
    - **`/opendap/`**:
        - `save_simar_point_to_TPAR.py`: Downloads simar data that will be used as BC. Taking into account what's specified in input_caxx.swn
    - **`/output/`**:
        - `check_matlab.py`: Reads the variables in .mat file created by SWAN
    - **`/plots/`**:
        - `validate.py`: Plots SWAN output against any validation file downloaded

- **`/timeGPT/`**: 
  - `timeGPT.py`: Runs timeGPT using each day swan fcst. It adjusts the model's result to what the tyde gauge located in the port could measure.
  - **`/combine/`**: Directory where combined SWAN ouput and tide gauge measurements DATA files are located
  - **`/DATA/`**: Directory where tide gauge downloaded and calculated DATA is stored
  - **`/pre/`**: Directory to pre-prepare timegpt DATA for forecast.
      - `download_and_calculate_mareograf_long.py`: Downloads tide gauge DATA and calculates Hsig and Period
      - `combine_datasets.py`: Combines SWAN output with calculated tide gauge DATA
      - `check_time_complete.py`: Checks timeseries has no missing dates. otherwise timeGPt fails
  - **`/prediction/`**: Directory where timeGPT prediction is stored
- **`.env`**: I have not uploaded mine. You will need to create a nixtla account and save the nixtla key here.

- **`.gitignore`**: Specifies which files and folders should be ignored by git.

- **`requirements.txt`**: A list of all the Python dependencies needed to run the project. You can install the necessary packages using `pip install -r requirements.txt`.

- **`README.md`**: This file explains the purpose and structure of the repository.
## How to use
If the Requirements are satisfied you should be able to run the operational system like:
```bash
./automate_forecast_allINPUTfiles_timeGPT_plot.sh
```
This will launch the forecast process. You’ll see output files created in the following locations:
- **SWAN predictions** → `./cases/palma/output/YYYYMM/`
- **TimeGPT predictions** → `./timeGPT/prediction/case_name/YYYYMM/`

**EXTRA**: How to run it daily using Crontab

To schedule daily runs, you can use the following crontab command (substitute with your actual necessities):
```cron
mins hour * * * /path/to/you/bash/script >> /path/to/your/log/file 2>&1
```
## Create a new case

Here are the steps:

1. **Create a new directory** in `cases` called `case_name`.

2. **Copy** `swan.exe` and `swanrun` to that directory.

3. **Copy the default INPUT file** (`input_ca00.swn`) to the folder and modify the following lines:

   - **Line 1**: Replace with your case name:
     ```
     PROJ 'CASENAME' 'ca00'
     ```
     Change `'CASENAME'` to your desired case name.

   - **Line 7**: Modify the grid coordinates to the study location:
     ```
     CGRID   [xpc] [ypc] [alpc] [xlenc] [ylenc] [mxc] [myc] CIRCLE 72 0.0345 1.00  34
     ```
     Use UTM coordinates. See more details in the [SWAN User Manual](https://swanmodel.sourceforge.io/download/zip/swanuse.pdf).

4. **Modify the Bash script**:

   - **Line 32**: Set your case name:
     ```bash
     CASE="case_name"
     ```

   - **Line 36**: Set your base directory PATH:
     ```bash
     BASE_DIR="PATH"
     ```
     
   - **Line 40**: Set the variable you want to predict with timegpt:
     ```bash
     GPT_target_VAR="var"
     ```

   - **Line 89**: Uncomment this line to generate the interpolated bathymetry for the new region.(remove the #)
     ```bash
     python3 /home/laloyo/waves-MED/scripts/bathy/download_and_interp_EMODNET_withcoastline_angle.py "$CASE" "$SWAN_CASE" "$LAT" "$LON"
     ```

5. **Enjoy your new case!**  
   Adapt the physics as wanted or needed :3


