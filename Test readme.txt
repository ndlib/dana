# Distribution Analysis & Navigation Algorithm (D.A.N.A.)

The Distribution Analysis & Navigation Algorithm framework contains: a data collection workbook with organizational measurement tables, a collections capacity summary sheet, and a customizable visual heatmap for your library. This workbook is paired with a strategic, logic-based shifting program to assist library workers by calculating capacity needs/surplus at a specified target fill rate. 

There are three PDF guides included with the files which go into detail for setting up the Distribution Analysis & Navigation Algorithm framework.

---

## Brief Overview

Staff first record measurements of empty space for each shelf onto pre-made spreadsheet tables. Using this data, a color-coded heatmap unique to a library’s stacks can be created. This allows for easy representation and a visually clear understanding of shelf capacities across the library. 

Beyond this, a user-friendly Python program (no Python familiarity is required) can process the summary of the collected measurement data to generate a detailed impact report. More than a simple list, it is a strategic plan that helps make data-driven decisions to most effectively utilize available library space. This report helps guide how much to move, from where, and to where for each range side in order to alleviate congested areas of the collection. If a potential shift is not feasible with current constraints, the program will notify the user and respond with how much surplus space is required. 

Orderly data collection increases accuracy of the end results. The heatmaps can be used to strategically target areas of the library that are experiencing capacity issues, and the shifting guide will greatly reduce shifting errors, stress, and time required to plan a shift.

All feedback is welcome. Please contact me if any of these tools were helpful or where the pain points were if they were not.

---

## Prior Art & Inspiration

I was inspired by Joshua Lambert’s project at Missouri State University. Please consider his program as an alternative if this framework does not work for you:
* [Code4Lib Article](https://journal.code4lib.org/articles/16577)
* [GitHub Repository (distichum/bookshift)](https://github.com/distichum/bookshift)

---

## 🧐 What's Inside?

An index of the repository files:

```text
Distribution Analysis & Navigation Algorithm
├── D.A.N.A - Blank Data Collection Workbook.xlsx
├── D.A.N.A. - Formatted Estimate From Rawdata CSV.xlsx
├── launch_library_tool.bat
└── library_app.py
PDF Guides & Documents
├── D.A.N.A. - (1st Step) Data Collection & Visual Mapping PDF Guide.pdf
├── D.A.N.A. - (2nd Step) Library Space Management Tool PDF Guide.pdf
├── D.A.N.A. - (3rd Step) CSV to Estimate Output PDF Guide.pdf
├── D.A.N.A. - FAQ Troubleshooting Guide.doc
└── Introduction.doc
Examples
├── Example CSV Data Collection Workbook - 11th Floor 2026 - Range Summary.csv
├── Example Data Collection Workbook - 11th Floor 2026.xlsx
└── Example D.A.N.A. - Formatted Estimate of 11th Floor Ranges 19b to 38b.xlsx

---

## Short Description:

<b>D.A.N.A - Blank Data Collection Workbook.xlsx:<b> Spreadsheet to record all measurement data, summarize your data and have the capability to allow you to create a visual heatmap.

<b>launch_library_tool.bat:<b> A Windows batch script that automates the setup and execution of the Library Space Management Tool. It installs required Python packages (Streamlit, Pandas and Plotly). Once complete the script will launch the library_app.py through a web application.

<b>library_app.py:<b> This file contains the python script to run the Library Space Management Tool which processes measurement data from the data collection workbook.

<b>D.A.N.A. - (1st Step) Data Collection & Visual Mapping PDF Guide.pdf:<b> Guides the user through setting up and operating the D.A.N.A - Blank Data Collection Workbook.xlsx

<b>D.A.N.A. - (2nd Step) Library Space Management Tool PDF Guide.pdf:<b> Guides the user through setting up and operating the strategic logic based shifting program.

<b>D.A.N.A. - (3rd Step) CSV to Estimate Output PDF Guide.pdf:<b> Guides the user through the final step of cleaning up and understanding the output CSV file from the shifting program.

<b>D.A.N.A. - FAQ Troubleshooting Guide.doc:<b> Guides users through potential problems and how to resolve them.

<b>Introduction.doc:<b> A short introduction of who I am and a brief overview of this project.  

<b>Example CSV Data Collection Workbook - 11th Floor 2026 - Range Summary.csv:<b> A populated workbook of measurement data collected from the 11th Floor of the Hesburgh Library and saved in csv format.

<b>Example Data Collection Workbook - 11th Floor 2026.xlsx:<b> The original fully populated workbook of measurement data collected from the 11th Floor of the Hesburgh Library.

<b>Example D.A.N.A. - Formatted Estimate of 11th Floor Ranges 19b to 38b.xlsx:<b> Shows an example of the formatted estimate which can be used as a guide to shift collections.

---

<b>LICENSE:<b> [Apache License 2.0](https://github.com/ndlib/dana/blob/main/LICENSE)