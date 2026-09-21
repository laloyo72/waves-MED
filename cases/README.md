# SWAN cases

##  Create your own case here!

This directory contains the configuration and input files for each SWAN case.

To create a new case, simply create a new directory inside `cases/`:

```text
cases/
└── your_case_name/
```

For example:

```text
cases/
└── palma/
```

Your case directory should contain the files and directories needed to run the SWAN simulation, following the structure of the existing cases.

A typical case may look like:

```text
your_case_name/
├── input/
│   ├── ...
│   └── TPAR_*.txt
├── output/
│   └── ...
├── input_ca00.swn
└── swanrun
```

### Before running the case

Make sure to:

1. Create your case directory.
2. Copy the required input files from an existing case or template. In ./start you have some example files.

###  Tip

If you are creating a case for a new location, it is recommended to start by copying an existing case and then modifying the necessary configuration files:

```bash
cp -r start/ cases/your_case_name
```

Then adapt the files to your new case.

> **Important:** Keep case-specific files inside your own case directory to keep the repository organised.

