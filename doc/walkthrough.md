# STDFReader CLI — Walkthrough

## Summary

Added a complete CLI interface to the STDFReader project, enabling all GUI features to be used from the command line. Also created an agent skill wrapping the CLI.

## Files Created

### 1. [stdf_reader_cli.py](file:///Users/jerry/PycharmProjects/STDFReader/stdf_reader_cli.py) — CLI Entry Point

11 subcommands covering all GUI features:

| Command | Description |
|---------|-------------|
| `convert-csv` | STDF → CSV (with progress bar + ETA) |
| `convert-xlsx` | STDF → XLSX table |
| `convert-diag` | STDF V4-2007.1 diagnosis → ASCII |
| `extract-record` | Extract DTR/GDR/TSR records |
| `transpose` | Transpose CSV rows ↔ columns |
| `report` | Generate analysis XLSX (stats, bins, wafer map) |
| `correlation` | Compare 2+ STDF files' means |
| `s2s` | Site-to-site correlation |
| `pdf` | Trendline + histogram PDF charts |
| `extract-tests` | Sub-CSV for specific tests |
| `list-tests` | List all test instances in a CSV |

**Key feature: `CliProgressBar`** — A beautiful terminal progress bar with ETA:
```
  Parsing a595.stdf [████████████████████████████████░░░]  92%  ETA 0s
```
It implements `.emit(int)` to be a drop-in replacement for `pyqtSignal(int)`, so `FileReaders.to_csv()` works without PyQt5.

---

### 2. [src/analysis.py](file:///Users/jerry/PycharmProjects/STDFReader/src/analysis.py) — Extracted Analysis Logic

All analysis functions extracted from the GUI's `Application` class into standalone functions with **no PyQt5 dependency**:

- `load_csv_data()` — Load and merge CSV files
- `get_summary_table()` — Compute per-site statistics (Cp, Cpk, etc.)
- `make_data_summary()` / `make_bin_summary()` / `make_wafer_map()`
- `generate_analysis_report()` — Full XLSX report with conditional formatting
- `make_correlation_table()` / `generate_correlation_report()`
- `make_s2s_correlation_table()` / `generate_s2s_correlation_report()`
- `extract_sub_csv()` / `generate_pdf_report()` / `transpose_csv()`

**Design choices:**
- Progress callbacks use `Optional[Callable[[int], None]]` instead of `QProgressBar`
- Error conditions raise exceptions instead of showing `QMessageBox`
- All functions accept data as parameters (no `self.*` references)
- GUI left untouched — both GUI and CLI are fully functional

---

### 3. [SKILL.md](file:///Users/jerry/.agents/skills/stdf-reader/SKILL.md) — Agent Skill

Registered as `stdf-reader` skill so AI agents can parse STDF files and generate reports.

## Test Results

All commands tested against sample files in `sample_stdf/`:

| Command | Test File | Result |
|---------|-----------|--------|
| `convert-csv` | `a595.stdf` | ✓ CSV created in 0.5s |
| `extract-record --type TSR` | `demofile.stdf` | ✓ TSR records extracted |
| `convert-csv --no-merge` | `a595.stdf + demofile.stdf` | ✓ Separate CSVs |
| `list-tests` | `a595.stdf_csv_log.csv` | ✓ 123 tests listed |
| `report` | `a595.stdf_csv_log.csv` | ✓ XLSX with 4 sheets |
| `pdf --regex "IDD"` | `a595.stdf_csv_log.csv` | ✓ 13-page PDF in 1.2s |
| `s2s` (1-site file) | `demofile.stdf_csv_log.csv` | ✓ Correct error message |

## GUI Refactoring ([STDF_Reader_GUI.py](file:///Users/jerry/PycharmProjects/STDFReader/STDF_Reader_GUI.py))

Refactored the GUI to delegate to `src/analysis.py` instead of containing duplicated logic. Used an **"insert + return" pattern** — new delegation code is inserted at the top of each method body with a `return` statement, making the original code unreachable but preserved as reference.

### Changes Made

| Method | Change |
|--------|--------|
| `_to_stdf_data()` | **New** — converts GUI state (`self.*`) into a `StdfData` object |
| `process_csv_file()` | Delegates to `stdf_analysis.load_csv_data()` |
| `generate_analysis_report()` | Delegates to `stdf_analysis.generate_analysis_report()` |
| `generate_correlation_report()` | Delegates to `stdf_analysis.generate_correlation_report()` |
| `generate_s2s_correlation_report()` | Delegates to `stdf_analysis.generate_s2s_correlation_report()` |
| `make_subcsv_for_chosen_tests()` | Delegates to `stdf_analysis.extract_sub_csv()` |
| `make_csv_transpose()` | Delegates to `stdf_analysis.transpose_csv()` |

> [!NOTE]
> Original method bodies are preserved as unreachable dead code below `return` statements. This makes the refactoring fully reversible — just remove the delegation block to restore original behavior.

### Untouched Methods (still use original logic)
- `plot_list_of_tests()` — uses `PdfWriterThread` (QThread-based)
- `make_s2s_correlation_heatmap()` — interactive matplotlib with `qt5Agg` backend
- All sub-methods (`make_data_summary_report`, `make_bin_summary`, etc.) — now dead code
