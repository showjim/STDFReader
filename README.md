# STDF Reader Tool

This project is designed for AP team to process and analyze Teradyne's STDF/STD file format.
![GUI](/img/Win_Capture.PNG)

## How to use

1. Convert STDF/STD file to ASCII CSV file by click button "Parse STD/STDF to .csv log", and select the stdf file, the CSV **Data Summary** output is shown as below;
![Data Summary](/img/Win_Capture4.PNG "Data Summary")
2. Upload the CSV file which generated in step 1 by click button "Upload parsed .csv file";
3. More buttons on the UI you can try to analyse STDF data, both loop/production data are accepted;
![Semantic description of image](/img/Win_Capture3.PNG)
4. You can generate XLSX version report of mean/cp/cpk by click "Generate data analysis report", **Data Statistics/Duplicate Test Number/Bin Summary/Wafer Map** are included;
![Semantic description of image](/img/Win_Capture2.PNG)
![Bin Summary](/img/Bin_Summary.PNG "Bin Summary")
![Wafer Map](/img/Wafer_Map.PNG "Wafer Map")
5. Or you can generate pdf report to review the trend and histogram;
![Semantic description of image](/img/PDF_Capture.PNG)
6. You can also upload parsed .csv with 2 STDF data to do correlation;
![Semantic description of image](/img/Win_Capture6.PNG)
![Semantic description of image](/img/Correlation_table.PNG)
![Semantic description of image](/img/Wafer_Map_Cmp.PNG)
7. This tool provide some other feathres, like convert STDF file to an .xlsx table or extract STR/PSR/PMR from diagnosis log to ASCII format, and you can also generate a sub-CSV file from chosen tests;
![Semantic description of image](/img/Win_Capture5.PNG)
![Semantic description of image](/img/Xlsx_Capture.PNG)
![Semantic description of image](/img/Diagnosis_Cap.PNG)