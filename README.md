# STDF Reader Tool

The STDF Reader Tool is a project designed for the AP team to process and analyze Teradyne's STDF/STD file format.

## Features

1. **Convert STDF/STD to CSV**: Parse STDF/STD files into CSV format for further analysis.
2. **Upload CSV files**: Upload the generated CSV files for data processing.
3. **Data analysis**: Perform various data analysis tasks, such as generating data statistics, duplicate test numbers, bin summaries, and wafer maps.
4. **Export reports**: Generate XLSX and PDF reports containing mean/cp/cpk values, data statistics, wafer maps, and more.
5. **Correlation**: Upload two parsed CSV files with STDF data to perform correlation analysis.
6. **Additional features**: Convert STDF files to XLSX tables, extract STR/PSR/PMR from diagnosis logs, and generate sub-CSV files from selected tests.
7. **Chat with STDF data in Natural language**: Use natural language to perform data analysis tasks, powered by Azure OpenAI.

![Sample Screenshots](/img/sample_screenshots.png)

## Setup Azure OpenAI (Optional)
To configure the application, you will need to create a `key.txt` file containing your Azure OpenAI API key and a `config.json` file with your desired settings.

### key.txt

Create a file named `key.txt` and add your Azure OpenAI API key as a single line in the file.

### config.json

Create a `config.json` file with the following configuration:

```json
{
    "CHATGPT_MODEL": "xxxxx",
    "OPENAI_API_BASE": "https://xxxxxx.openai.azure.com/",
    "OPENAI_API_VERSION": "xxxxx",
    "EMBEDDING_MODEL": "xxxxx",
    "EMBEDDING_MODEL_VERSION": "xxxxx"
}
```

## Acknowledgments

- The Python community for the excellent libraries used in this project
- Thanks to Casey, all I have done are based on this repo [cmars/pystdf](https://github.com/cmars/pystdf)
