# STDF Reader Tool

**A Comprehensive STDF/STD File Analysis Solution**

[![PyPI Version](https://img.shields.io/pypi/v/stdf-reader.svg)](https://pypi.org/project/stdf-reader/)
[![Python Versions](https://img.shields.io/pypi/pyversions/stdf-reader.svg)](https://pypi.org/project/stdf-reader/)
[![License](https://img.shields.io/pypi/l/stdf-reader.svg)](https://github.com/showjim/STDFReader/blob/master/LICENSE)
[![PyPI Downloads](https://img.shields.io/pypi/dm/stdf-reader.svg)](https://pypi.org/project/stdf-reader/)

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
  - [CLI Usage](#cli-usage)
  - [GUI Usage](#gui-usage)
- [Screenshots](#screenshots)
- [License](#license)

---

## Overview

The **STDF Reader Tool** is a comprehensive desktop application and command-line toolkit designed for the AP (Application Engineering) team to process and analyze Teradyne's STDF (Standard Test Data Format) and STD files. This tool provides an intuitive graphical interface for parsing test data, generating statistical reports, and performing advanced data analysis operations.

STDF is the industry-standard format for storing test data from semiconductor manufacturing. This tool simplifies the process of extracting valuable insights from test data, enabling engineers to:

- Quickly convert raw test data into analyzable formats
- Generate comprehensive statistical reports (CP, CPK, mean, standard deviation)
- Visualize test results through wafer maps and histograms
- Perform correlation analysis between different test lots
- Extract specific test results for detailed investigation

### PyPI Package

This project is available on PyPI as [stdf-reader](https://pypi.org/project/stdf-reader/):

> STDF (Standard Test Data Format) file reader, parser, and analysis tool for semiconductor test data.

---

## Features

### Core Functionality

#### 1. **STDF/STD to CSV Conversion**
- Parse binary STDF/STD files into human-readable CSV format
- Support for multiple STDF versions (V4, V42007)
- Fast and efficient parsing with configurable options
- Ability to skip specific record types for improved performance

#### 2. **CSV File Processing**
- Upload and process previously generated CSV files
- Handle large datasets efficiently
- Support for partial data loading with row limits
- Real-time data validation and error handling

#### 3. **Comprehensive Data Analysis**
- **Statistical Analysis**: Calculate mean, standard deviation, min, max values
- **Process Capability**: Compute CP and CPK indices for process monitoring
- **Duplicate Detection**: Identify duplicate test numbers with different names
- **Bin Summaries**: Generate detailed bin distribution reports
- **Wafer Mapping**: Visualize test results across wafer coordinates

#### 4. **Report Generation**
- **XLSX Reports**: Create Excel workbooks with:
  - Multiple sheets for different test analyses
  - Formatted tables with conditional formatting
  - Statistical summaries and charts
  - CP/CPK calculations with color-coded results
- **PDF Reports**: Generate professional PDF documents containing:
  - Test result summaries
  - Wafer map visualizations
  - Statistical charts and graphs
  - Custom formatting and branding options

#### 5. **Correlation Analysis**
- Compare test results between two different lots or test runs
- Identify correlations between test parameters
- Scatter plot visualization with trend lines
- Statistical correlation coefficients

#### 6. **Advanced Features**
- **XLSX Conversion**: Direct STDF to Excel table conversion
- **Diagnosis Log Parsing**: Extract STR (Software Test Record), PSR (Part Site Record), and PMR (Part Master Record) from diagnosis logs
- **Sub-CSV Generation**: Create filtered CSV files containing only selected tests
- **Table Transposition**: Convert between row-based and column-based data representations
- **ASCII Conversion**: Convert legacy STDF formats to ASCII-readable format

#### 7. **Data Visualization**
- Histograms for test value distributions
- Scatter plots for correlation analysis
- Wafer maps with bin code visualization
- Trend lines for temporal analysis
- 3D visualization capabilities

---

## Installation

### Prerequisites

- Python 3.9 or higher
- pip package manager
- Windows, macOS, or Linux operating system

### Option 1: Install from PyPI (Recommended)

```bash
# Basic installation (CLI + analysis tools)
pip install stdf-reader

# With GUI support
pip install stdf-reader[gui]
```

### Option 2: Install from Source

#### Step 1: Clone the Repository

```bash
git clone https://github.com/showjim/STDFReader.git
cd STDFReader
```

#### Step 2: Create Virtual Environment (Recommended)

```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

#### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Building an Executable (Optional)

To create a standalone executable:

```bash
pyinstaller STDF_Reader_GUI.spec
```

The executable will be located in the `dist/` directory.

---

## Usage

### CLI Usage

After installing via pip, the CLI tool is available as `stdf-reader`:

```bash
# Show available commands
stdf-reader --help

# Parse STDF/STD file(s) to CSV
stdf-reader convert-csv <file(s)> [-o output_name]
# Options: --ignore-tnum, --ignore-chnum, --no-merge

# Parse STDF/STD file to XLSX table
stdf-reader convert-xlsx <file>

# Generate analysis report (XLSX) from CSV
stdf-reader report <csv_file(s)> [-o output.xlsx]

# Generate PDF charts for selected tests
stdf-reader pdf <csv_file(s)> [-o output.pdf]
# Options: --tests "name", --regex "pattern", --all, --no-limits, --group-by-file

# Generate correlation report
stdf-reader correlation <csv_file(s)> [-o output.xlsx]

# Generate site-to-site correlation report
stdf-reader s2s <csv_file(s)> [-o output.xlsx] [--cherry-pick "1,3,5"]

# Extract specific records (DTR, GDR, TSR, GDR_ZIP)
stdf-reader extract-record <file> --type <record_type>

# Extract sub-CSV for specific tests
stdf-reader extract-tests <csv_file(s)> [-o output.csv]

# List all test instances in a CSV file
stdf-reader list-tests <csv_file(s)> [--filter "pattern"]

# Transpose a CSV file (rows <-> columns)
stdf-reader transpose <csv_file> [-o output.csv]

# Parse diagnosis log
stdf-reader convert-diag <file>
```

### GUI Usage

After installing with GUI support (`pip install stdf-reader[gui]`), launch the GUI:

```bash
stdf-reader-gui
```

Or run directly from source:

```bash
python STDF_Reader_GUI.py
```

#### Quick Start Guide

1. **Launch the Application**
   - Run `stdf-reader-gui` or execute the built binary
   - The main window will open with the "Some Tools" tab active

2. **Load an STDF File**
   - Click the "Select STDF/STD File" button
   - Navigate to your test data file and select it
   - The file will be parsed into `*.csv` format
   - Load the CSV file

3. **Generate Basic Reports**
   - Use the "Select Test" dropdown to choose a specific test
   - Click "Generate PDF" to create a PDF report
   - Click "Generate XLSX" to create an Excel report

4. **Perform Data Analysis**
   - Navigate to different tabs for various analysis options
   - Use "Data Statistics" for comprehensive statistical analysis
   - Access "Wafer Map" for spatial visualization
   - Try "Correlation" to compare two datasets

---

## Screenshots

![Sample Screenshots](/img/sample_screenshots.png)

---

## Special Thanks

- The original PySTDF library for providing robust STDF parsing capabilities
- The matplotlib and numpy communities for exceptional visualization and numerical computing tools
- All users who have provided feedback and bug reports to improve this tool

---

## License

This project is licensed under the [GNU General Public License v2.0](LICENSE).

---

<div align="center">

**Built for the semiconductor testing community**

If you find this tool useful, please consider giving it a star!

</div>
