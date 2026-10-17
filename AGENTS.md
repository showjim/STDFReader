# AGENTS.md

This file provides guidance to AI coding agents (Claude Code, Codex, Gemini CLI, Cursor, and others) when working with code in this repository.

## Project

`stdf-reader` parses and analyzes STDF (Standard Test Data Format) semiconductor test data. It ships three things: a CLI (`stdf-reader`), an optional PyQt5 GUI (`stdf-reader-gui`), and `pystdf`, a bundled forked STDF parser. Distributed on PyPI under GPL-2.0.

## Commands

```bash
# Activate the project venv
source .venv/bin/activate

# Editable install
pip install -e ".[gui,dev]"        # or: pip install -r requirements.txt

# CLI (all subcommands)
stdf-reader --help
python -m stdf_reader.cli --help   # same entry point, no install needed

# GUI
stdf-reader-gui
python -m stdf_reader.gui

# Build distributions
python -m build                    # dist/*.whl + *.tar.gz

# Standalone Windows executable (uses the legacy root script, not the package)
pyinstaller --onefile --icon=./img/icon.ico STDF_Reader_GUI.py

# No test suite exists. CI (on tags `V*`) smoke-tests on Python 3.11/3.13/3.14:
pip install -e . && stdf-reader --help
stdf-reader extract-record sample_stdf/demofile.stdf --type MIR
# then builds the Windows exe on Python 3.11.
```

Sample STDF inputs are in [sample_stdf/](sample_stdf/) (`a595.stdf`, `demofile.stdf`, `lot2.stdf`, `lot3.stdf`). There is no pytest/unittest setup; `test/transpose.py` is a scratch script.

## Package layout

- [stdf_reader/](stdf_reader/) — the installed package. `__version__` lives in [stdf_reader/__init__.py](stdf_reader/__init__.py) and drives the setuptools dynamic version.
  - [cli.py](stdf_reader/cli.py) — argparse CLI; lazy-imports heavy modules inside each `cmd_*` so PyQt5 is not required.
  - [gui.py](stdf_reader/gui.py) — PyQt5 main window (`Application` class).
  - [FileRead.py](stdf_reader/FileRead.py) — STDF → CSV/XLSX/ASCII conversion sinks.
  - [analysis.py](stdf_reader/analysis.py) — GUI-free report/statistics/chart generation (CLI uses this; GUI delegates to it).
  - [Backend.py](stdf_reader/Backend.py) — matplotlib plotting primitives plus Cp/Cpk math, shared by GUI and `analysis.py`.
  - [Threads.py](stdf_reader/Threads.py) — `QThread` wrappers around conversion/report work for the GUI.
- [pystdf/](pystdf/) — forked PySTDF parser (GPL). `pystdf/V4.py` defines every STDF record type and its `fieldMap`; `pystdf/IO.py` holds the binary `Parser`. `pystdf/explorer/` is dead wxPython code, excluded from the package.
- Root-level `STDF_Reader_GUI.py` is a pre-refactor copy of `stdf_reader/gui.py`, kept because the PyInstaller CI step and README build from it; do not treat it as the source of truth. `V4_2007.py` is unused.

## Data flow

1. **Parse** — `FileReaders.to_csv()` ([FileRead.py](stdf_reader/FileRead.py)) opens a `.std/.stdf` (or `.gz`) and feeds it to `pystdf.IO.Parser`.
2. **Sink events** — `pystdf.Pipeline` is an event bus: a sink passed to `Parser.addSink()` gets `after_begin`, `after_send(rectype, fields)`, `after_complete` callbacks. `MyTestResultProfiler` is the main sink; it accumulates per-test PTR/MPR results and PIR/PRR part metadata.
3. **CSV contract** — `write_to_csv()` emits a **5-row multi-level header** per test column: `(test name, high limit, low limit, units, test number)`. The first 16 columns are fixed part metadata: `FILE_NAM, TESTER_NAM, START_T, PGM_NAM, JOB_NAM, LOT_ID, WAFER_ID, SITE_NUM, X_COORD, Y_COORD, PART_ID, RC, HARD_BIN, SOFT_BIN, BIN_DESC, TEST_T`. Test values may carry `(F)`/`(A)` fail/abort markers that analysis strips.
4. **Analyze** — `load_csv_data()` reads with `pd.read_csv(..., header=[0,1,2,3,4])`, flattens columns into `"<number> - <name>"` strings, merges multiple CSVs, and returns an `StdfData` object. Every report function takes that object; it is the shared interface between CLI and GUI (`Application._to_stdf_data()` builds one from GUI state).

When changing the CSV format, update both the writer in `FileRead.py` and the 16-column offset / header depth assumptions in `analysis.load_csv_data()`.

## Conventions and gotchas

- **No PyQt5 in `analysis.py`.** Keep report/reporting logic importable without the GUI extra. matplotlib must use the `Agg` backend there.
- **Progress callbacks** are `Optional[Callable[[int], None]]` (0–100). The GUI passes `self.progress_bar.setValue`; the CLI passes `CliProgressBar.emit`, which deliberately duck-types `pyqtSignal` (`.emit()`, no-op `.connect()`) so `FileReaders.to_csv()` runs headless.
- **GUI dead-code pattern.** Most report methods in `gui.py` delegate to `analysis.py` and then `return`; the original implementation is retained below the return as unreachable reference code. Look for `# --- Original code below (kept as reference, unreachable) ---` before assuming code is live.
- **STDF record handling** special cases matter: `EXEC_TYP` (`93000` vs IG-XL) changes PMR field usage; MPR records fan out into multiple pseudo-tests; duplicate test instances get `_AppearedN` suffixes; `ignore_tnum` sets all test numbers to `0`, `ignore_chnum` drops the third whitespace token of a test name. Preserve these when touching `MyTestResultProfiler.after_send`.
- **Logging**: CLI logs to `%LOCALAPPDATA%/stdf-reader/app.log` (or `~/.stdf-reader/app.log`); GUI logs to `app.log` beside the script (`sys._MEIPASS` when frozen).
- **Versioning/release**: bump `stdf_reader/__init__.py:__version__`, tag `V*`, and both GitHub workflows run — `python-app.yml` smoke-tests and builds a Windows exe, `publish.yml` builds and publishes to PyPI via trusted publishing.
- `.gitignore` excludes all data artifacts (`*.stdf`, `*.csv`, `*.xlsx`, `*.pdf`, `*.log`), so newly generated outputs won't show in `git status`.
