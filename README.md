# STDF Reader Tool

**A Comprehensive STDF/STD File Analysis Solution**

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Screenshots](#screenshots)

---

## Overview

The **STDF Reader Tool** is a comprehensive desktop application designed for the AP (Application Engineering) team to process and analyze Teradyne's STDF (Standard Test Data Format) and STD files. This tool provides an intuitive graphical interface for parsing test data, generating statistical reports, and performing advanced data analysis operations.

STDF is the industry-standard format for storing test data from semiconductor manufacturing. This tool simplifies the process of extracting valuable insights from test data, enabling engineers to:

- Quickly convert raw test data into analyzable formats
- Generate comprehensive statistical reports (CP, CPK, mean, standard deviation)
- Visualize test results through wafer maps and histograms
- Perform correlation analysis between different test lots
- Extract specific test results for detailed investigation

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

- Python 3.10 or higher
- pip package manager
- Windows, macOS, or Linux operating system

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-username/STDFReader.git
cd STDFReader
```

### Step 2: Create Virtual Environment (Recommended)

```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Run the Application

```bash
python STDF_Reader_GUI.py
```

### Building an Executable (Optional)

To create a standalone executable:

```bash
pyinstaller STDF_Reader_GUI.spec
```

The executable will be located in the `dist/` directory.

---

## Usage

### Quick Start Guide

1. **Launch the Application**
   - Run `STDF_Reader_GUI.py` or execute the built binary
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

### Special Thanks

- The original PySTDF library for providing robust STDF parsing capabilities
- The matplotlib and numpy communities for exceptional visualization and numerical computing tools
- All users who have provided feedback and bug reports to improve this tool

---

<div align="center">

**Built with ❤️ for the semiconductor testing community**

⭐ If you find this tool useful, please consider giving it a star!

</div>
