# Here we explain the steps in order to add timeGPT prediction to your case
# First we need:
# 	1. long term timeseries of what the tide gauge measures:
# 	2. long simulation of SWAN calculation
# Lets go to ./pre/ directory:
#
# --------------------------------------------------------
# STEP 1: tide gauge
#
# 1. python3 download_and_calculate_mareograf_long.py 
# 2. choose the dates etc
# ---> you will see now you have the timseries: ./DATA/mareograf/calculated/{case_name}/wave_parameters_{case_name}_{start_date}_{end_date}.csv
#
# ---------------------------------------------------------
#
# STEP 2: create SWAN long simulation
# 0. download the boundary conditions for the long simulation:
#   $ cd ../scripts/opendap/
#   $ python3 save_simar_point_to_TPAR_year.py
# ---> you will need to choose case, start and end date
# ---> you will see now you have the downloaded timeseries in: ../../cases/{case_name}/input/TPAR_simar_{start_date}_{end_date}_{lat}_{lon}.txt
# as we create just one boundary file we cp this one to all the boundaries (little trick)
#   $ cd ../../cases/{case_name}/input/
#   $ cp TPAR_simar_{start_date}_{end_date}_{lat}_{lon}.txt TPAR_north_simar_{start_date}_{end_date}_{lat}_{lon}.txt 
#   $ cp TPAR_simar_{start_date}_{end_date}_{lat}_{lon}.txt TPAR_south_simar_{start_date}_{end_date}_{lat}_{lon}.txt
#   $ cp TPAR_simar_{start_date}_{end_date}_{lat}_{lon}.txt TPAR_east_simar_{start_date}_{end_date}_{lat}_{lon}.txt
#   $ cp TPAR_simar_{start_date}_{end_date}_{lat}_{lon}.txt TPAR_west_simar_{start_date}_{end_date}_{lat}_{lon}.txt
#
# Now in your case directory
# 1. cp input_ca00.swn to input_cat0.swn and modify the simulation dates and paths to run a long simulation
# 2. Run swan long simulation. Modify ca00 to cat0 in swanrun and 
#   $ ./swanrun
# --> you will obtain SWAn prediction ../cases/{case_name}/output/tableP_cat0_F3_{start_date}_{end_date}.txt
#
# ---------------------------------------------------------
#
# STEP 3: combine both timeseries
# 1. We need to combine both dataset let's go to ./timeGPT/pre/
# --> change PATHs in combine_datasets.py
#   $ python3 combine_datasets.py
# --> you will obtain ../combine/{case_name}/Hsig_exog_vars_swan-calcMareograf.csv
# 2. Check the combined dataset is complete: 
# As timeGPT needs all the timeseries we have an script to check that the downloaded tide gauge values are okkk: check_time_complete_and_NaN.py
# change PATH and execute 
#   $ python3 check_time_complete_and_NaN.py
#
# --------------------------------------------------------  
# Now we are ready to run long timeGPT module!!!!!!!!!!!!!!!!!!!!!
########^_^#######
