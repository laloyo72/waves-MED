# TimeGPT prediction workflow

This folder contains the scripts needed to prepare the input data and run **TimeGPT predictions** for a given SWAN case.

The workflow requires two long-term time series:

1. **Tide gauge observations** — long-term time series of the wave parameters measured by the tide gauge.
2. **SWAN simulation** — a long-term SWAN simulation covering the same period.

The workflow is divided into three steps:

1. Download and prepare the tide gauge time series.
2. Run a long SWAN simulation.
3. Combine both datasets and check the resulting time series.

---

## 1. Tide gauge time series

First, go to the `pre/` directory:

```bash
cd timeGPT/pre/
```

Run:

```bash
python3 download_and_calculate_mareograf_long.py
```

The script will ask you to select the **case**, **start date**, and **end date**.

After running the script, the calculated tide gauge time series will be stored in:

```text
./DATA/mareograf/calculated/{case_name}/wave_parameters_{case_name}_{start_date}_{end_date}.csv
```

---

## 2. Create a long SWAN simulation

### 2.1 Download the boundary conditions

First, download the boundary conditions required for the long simulation.

Go to:

```bash
cd ../scripts/opendap/
```

Run:

```bash
python3 save_simar_point_to_TPAR_year.py
```

Select the **case**, **start date**, and **end date** when prompted.

The downloaded boundary time series will be stored in:

```text
../../cases/{case_name}/input/TPAR_simar_{start_date}_{end_date}_{lat}_{lon}.txt
```

### 2.2 Copy the boundary file

Since we currently use the same boundary time series for all four SWAN boundaries, copy the downloaded file to the north, south, east, and west boundaries:

```bash
cd ../../cases/{case_name}/input/
```

Then:

```bash
cp TPAR_simar_{start_date}_{end_date}_{lat}_{lon}.txt \
   TPAR_north_simar_{start_date}_{end_date}_{lat}_{lon}.txt

cp TPAR_simar_{start_date}_{end_date}_{lat}_{lon}.txt \
   TPAR_south_simar_{start_date}_{end_date}_{lat}_{lon}.txt

cp TPAR_simar_{start_date}_{end_date}_{lat}_{lon}.txt \
   TPAR_east_simar_{start_date}_{end_date}_{lat}_{lon}.txt

cp TPAR_simar_{start_date}_{end_date}_{lat}_{lon}.txt \
   TPAR_west_simar_{start_date}_{end_date}_{lat}_{lon}.txt
```

### 2.3 Prepare the SWAN input

Go to the case directory:

```text
cases/{case_name}/
```

Copy the standard input file:

```bash
cp input_ca00.swn input_cat0.swn
```

Then modify `input_cat0.swn` to:

* Use the desired simulation period.
* Update the required input/output paths.
* Adapt any other parameters needed for the long simulation.

### 2.4 Run SWAN

Modify `swanrun` so that it uses `cat0` instead of `ca00`.

Then run:

```bash
./swanrun
```

The long SWAN simulation will produce a time series similar to:

```text
../cases/{case_name}/output/tableP_cat0_F3_{start_date}_{end_date}.txt
```

---

## 3. Combine the time series

Once both the tide gauge and SWAN time series have been generated, they need to be combined into a single dataset for TimeGPT.

Go to:

```bash
cd timeGPT/pre/
```

### 3.1 Combine the datasets

Open:

```text
combine_datasets.py
```

and update the required paths.

Then run:

```bash
python3 combine_datasets.py
```

The resulting combined dataset will be stored in:

```text
../combine/{case_name}/Hsig_exog_vars_swan-calcMareograf.csv
```

---

### 3.2 Check the time series

TimeGPT requires a complete time series without missing timestamps or invalid values.

The script:

```text
check_time_complete_and_NaN.py
```

checks the combined dataset for:

* Missing timestamps.
* NaN values.
* Problems in the time series continuity.

Update the required path and run:

```bash
python3 check_time_complete_and_NaN.py
```

Make sure that the resulting dataset is complete before continuing.

---

## 4. Run TimeGPT

Once the previous steps have been completed successfully, the combined dataset is ready to be used by the **TimeGPT prediction module**.

You can now uncomment timeGPT line in the general bash script, and run the timeGPt preditction!

> **Note:** Make sure that the SWAN and tide gauge datasets cover the same period and have a consistent time resolution before running TimeGPT.

