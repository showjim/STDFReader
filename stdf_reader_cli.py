#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
STDF Reader CLI — Command-line interface for STDF file processing and analysis.

Usage:
    python stdf_reader_cli.py <command> [options]

Commands:
    convert-csv      Parse STDF file(s) to CSV log
    convert-xlsx     Parse STDF file to XLSX table
    convert-diag     Convert STDF V4-2007.1 diagnosis to ASCII CSV
    extract-record   Extract a single record type (DTR/GDR/TSR) to CSV
    report           Generate analysis report (xlsx) from CSV
    correlation      Generate correlation report from CSV (needs 2+ STDFs)
    s2s              Generate site-to-site correlation report
    pdf              Generate PDF charts for selected tests
    extract-tests    Extract sub-CSV for specific tests
    transpose        Transpose a CSV file (rows <-> columns)
"""

import argparse
import sys
import os
import time
import logging
import re

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# Terminal Progress Bar
# ---------------------------------------------------------------------------

class CliProgressBar:
    """
    Beautiful terminal progress bar, compatible with pyqtSignal(int).emit().
    Drop-in replacement so FileReaders.to_csv() works without PyQt5.
    """

    def __init__(self, description="Processing", width=35):
        self.description = description
        self.width = width
        self._last_pct = -1
        self._start_time = time.time()

    def emit(self, pct):
        """Called with an integer 0–100 to update the progress bar."""
        pct = max(0, min(pct, 100))
        if pct == self._last_pct:
            return
        self._last_pct = pct

        filled = int(self.width * pct / 100)
        bar = '█' * filled + '░' * (self.width - filled)

        elapsed = time.time() - self._start_time
        if pct > 0:
            eta = elapsed / pct * (100 - pct)
            time_str = f"ETA {eta:.0f}s"
        else:
            time_str = "..."

        sys.stdout.write(f'\r  {self.description} [{bar}] {pct:3d}%  {time_str}  ')
        sys.stdout.flush()

        if pct >= 100:
            sys.stdout.write(f'\r  {self.description} [{bar}] {pct:3d}%  done in {elapsed:.1f}s  \n')

    def connect(self, *args):
        """No-op for compatibility with pyqtSignal.connect()."""
        pass


# ---------------------------------------------------------------------------
# Conversion Commands
# ---------------------------------------------------------------------------

def cmd_convert_csv(args):
    """Convert STDF file(s) to CSV log."""
    from stdf_reader.FileRead import FileReaders

    file_paths = args.files
    for fp in file_paths:
        if not os.path.exists(fp):
            print(f"  ✗ Error: File not found: {fp}", file=sys.stderr)
            return 1

    if args.no_merge or len(file_paths) == 1:
        # Process each file separately
        for fp in file_paths:
            output_name = args.output if args.output else fp
            progress = CliProgressBar(f"Parsing {os.path.basename(fp)}")
            FileReaders.to_csv([fp], output_name, progress,
                               args.ignore_tnum, args.ignore_chnum)
            print(f"  ✓ Output: {output_name}_csv_log.csv")
    else:
        # Merge all files into one CSV
        if args.output:
            output_name = args.output
        else:
            t = time.strftime("%Y%m%d%H%M%S")
            output_name = os.path.join(os.path.dirname(file_paths[0]),
                                       f'output_data_summary_{t}')
        progress = CliProgressBar("Parsing STDF files")
        FileReaders.to_csv(file_paths, output_name, progress,
                           args.ignore_tnum, args.ignore_chnum)
        print(f"  ✓ Output: {output_name}_csv_log.csv")
    return 0


def cmd_convert_xlsx(args):
    """Convert STDF file to XLSX table."""
    from stdf_reader.FileRead import FileReaders

    fp = args.file
    if not os.path.exists(fp):
        print(f"  ✗ Error: File not found: {fp}", file=sys.stderr)
        return 1

    print(f"  Parsing {os.path.basename(fp)} to XLSX...")
    FileReaders.to_excel(fp)
    print(f"  ✓ Output: {fp}_excel.xlsx")
    return 0


def cmd_convert_diag(args):
    """Convert STDF V4-2007.1 diagnosis to ASCII CSV."""
    from stdf_reader.FileRead import FileReaders

    fp = args.file
    if not os.path.exists(fp):
        print(f"  ✗ Error: File not found: {fp}", file=sys.stderr)
        return 1

    print(f"  Parsing diagnosis from {os.path.basename(fp)}...")
    FileReaders.to_ASCII(fp)
    print(f"  ✓ Output: {fp}_diag_log.csv")
    return 0


def cmd_extract_record(args):
    """Extract a single record type to CSV."""
    from stdf_reader.FileRead import FileReaders

    fp = args.file
    rec_type = args.type.upper()
    if not os.path.exists(fp):
        print(f"  ✗ Error: File not found: {fp}", file=sys.stderr)
        return 1

    extract_zip = rec_type.endswith('_ZIP')
    if extract_zip:
        rec_type = rec_type.split('_')[0]

    print(f"  Extracting {rec_type} records from {os.path.basename(fp)}...")
    FileReaders.rec_to_csv(fp, rec_type, extract_zip)
    print(f"  ✓ Output: {fp}_{rec_type}_Rec.csv")
    return 0


def cmd_transpose(args):
    """Transpose a CSV file (rows <-> columns)."""
    from stdf_reader.analysis import transpose_csv

    fp = args.file
    if not os.path.exists(fp):
        print(f"  ✗ Error: File not found: {fp}", file=sys.stderr)
        return 1

    output = args.output if args.output else None
    print(f"  Transposing {os.path.basename(fp)}...")
    transpose_csv(fp, output)
    return 0


# ---------------------------------------------------------------------------
# Analysis Commands
# ---------------------------------------------------------------------------

def _load_data(args):
    """Helper: load CSV data with common options."""
    from stdf_reader.analysis import load_csv_data

    file_paths = args.files if hasattr(args, 'files') else [args.file]
    for fp in file_paths:
        if not os.path.exists(fp):
            print(f"  ✗ Error: File not found: {fp}", file=sys.stderr)
            sys.exit(1)

    cherry_pick = None
    if hasattr(args, 'cherry_pick') and args.cherry_pick:
        cherry_pick = [int(s) for s in args.cherry_pick.split(',')]

    print(f"  Loading {len(file_paths)} CSV file(s)...")
    data = load_csv_data(file_paths, cherry_pick)
    print(f"  Loaded {data.df_csv.shape[0]} parts, {len(data.list_of_test_numbers)} tests, "
          f"{data.number_of_sites} sites")
    return data


def cmd_report(args):
    """Generate analysis report (xlsx) from CSV."""
    from stdf_reader.analysis import generate_analysis_report

    data = _load_data(args)
    progress = CliProgressBar("Generating report")
    generate_analysis_report(data, args.output, progress_cb=progress.emit)
    return 0


def cmd_correlation(args):
    """Generate correlation report from CSV (needs 2+ STDFs merged)."""
    from stdf_reader.analysis import generate_correlation_report

    data = _load_data(args)
    progress = CliProgressBar("Generating correlation")
    generate_correlation_report(data, args.output, progress_cb=progress.emit)
    return 0


def cmd_s2s(args):
    """Generate site-to-site correlation report."""
    from stdf_reader.analysis import generate_s2s_correlation_report

    data = _load_data(args)
    progress = CliProgressBar("Generating S2S report")
    generate_s2s_correlation_report(data, args.output, progress_cb=progress.emit)
    return 0


def cmd_pdf(args):
    """Generate PDF charts for selected tests."""
    from stdf_reader.analysis import generate_pdf_report

    data = _load_data(args)

    # Determine selected tests
    if args.all:
        selected_tests = data.list_of_test_numbers_string
    elif args.tests:
        selected_tests = args.tests
    elif args.regex:
        # Match test names by regex pattern
        pattern = args.regex
        selected_tests = [t for t in data.list_of_test_numbers_string
                          if re.search(pattern, t)]
        if not selected_tests:
            print(f"  ✗ No tests matched pattern: {pattern}")
            return 1
        print(f"  Matched {len(selected_tests)} tests")
    else:
        print("  ✗ Please specify tests with --tests, --regex, or --all")
        return 1

    progress = CliProgressBar("Generating PDF")
    generate_pdf_report(data, selected_tests, args.output,
                        limits_toggled=not args.no_limits,
                        group_by_file=args.group_by_file,
                        progress_cb=progress.emit)
    return 0


def cmd_extract_tests(args):
    """Extract sub-CSV for specific tests."""
    from stdf_reader.analysis import extract_sub_csv

    data = _load_data(args)

    if args.tests:
        selected_tests = args.tests
    elif args.regex:
        pattern = args.regex
        selected_tests = [t for t in data.list_of_test_numbers_string
                          if re.search(pattern, t)]
        if not selected_tests:
            print(f"  ✗ No tests matched pattern: {pattern}")
            return 1
        print(f"  Matched {len(selected_tests)} tests")
    else:
        print("  ✗ Please specify tests with --tests or --regex")
        return 1

    extract_sub_csv(data, selected_tests, args.output)
    return 0


def cmd_list_tests(args):
    """List all test instances in a CSV file."""
    data = _load_data(args)

    pattern = args.filter if hasattr(args, 'filter') and args.filter else None

    tests = data.list_of_test_numbers_string
    if pattern:
        tests = [t for t in tests if re.search(pattern, t)]

    print(f"\n  {'#':<6} {'Test Instance'}")
    print(f"  {'─' * 6} {'─' * 60}")
    for i, t in enumerate(tests):
        print(f"  {i + 1:<6} {t}")
    print(f"\n  Total: {len(tests)} test(s)")
    return 0


# ---------------------------------------------------------------------------
# Argument Parser
# ---------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        prog='stdf_reader_cli',
        description='STDF Reader CLI — Parse, analyze, and report on STDF test data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert STDF to CSV
  python stdf_reader_cli.py convert-csv input.stdf

  # Convert multiple STDFs to a single merged CSV
  python stdf_reader_cli.py convert-csv file1.stdf file2.stdf

  # Generate analysis report from CSV
  python stdf_reader_cli.py report data_csv_log.csv

  # Generate PDF for specific tests (regex)
  python stdf_reader_cli.py pdf data_csv_log.csv --regex "VDD.*"

  # List all tests in a CSV
  python stdf_reader_cli.py list-tests data_csv_log.csv
        """)

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # --- convert-csv ---
    p = subparsers.add_parser('convert-csv', help='Parse STDF/STD file(s) to CSV log')
    p.add_argument('files', nargs='+', help='STDF file(s) to parse')
    p.add_argument('-o', '--output', help='Output file base name (default: auto)')
    p.add_argument('--ignore-tnum', action='store_true',
                   help='Ignore test number (match by name only)')
    p.add_argument('--ignore-chnum', action='store_true',
                   help='Ignore channel number in test name')
    p.add_argument('--no-merge', action='store_true',
                   help='Output separate CSV per file (default: merge into one)')
    p.set_defaults(func=cmd_convert_csv)

    # --- convert-xlsx ---
    p = subparsers.add_parser('convert-xlsx', help='Parse STDF/STD file to XLSX table')
    p.add_argument('file', help='STDF file to parse')
    p.set_defaults(func=cmd_convert_xlsx)

    # --- convert-diag ---
    p = subparsers.add_parser('convert-diag',
                              help='Convert STDF V4-2007.1 diagnosis to ASCII CSV')
    p.add_argument('file', help='STDF file to parse')
    p.set_defaults(func=cmd_convert_diag)

    # --- extract-record ---
    p = subparsers.add_parser('extract-record',
                              help='Extract a single record type to CSV')
    p.add_argument('file', help='STDF file to parse')
    p.add_argument('--type', required=True, choices=['DTR', 'GDR', 'TSR', 'GDR_ZIP'],
                   help='Record type to extract')
    p.set_defaults(func=cmd_extract_record)

    # --- transpose ---
    p = subparsers.add_parser('transpose', help='Transpose a CSV file (rows <-> columns)')
    p.add_argument('file', help='CSV file to transpose')
    p.add_argument('-o', '--output', help='Output file path (default: <input>_transposed.csv)')
    p.set_defaults(func=cmd_transpose)

    # --- report ---
    p = subparsers.add_parser('report', help='Generate analysis report (xlsx) from CSV')
    p.add_argument('files', nargs='+', help='CSV file(s) to analyze')
    p.add_argument('-o', '--output', help='Output xlsx path (default: auto)')
    p.add_argument('--cherry-pick', help='Site numbers to pick, one per file (e.g. "1,3,5")')
    p.set_defaults(func=cmd_report)

    # --- correlation ---
    p = subparsers.add_parser('correlation',
                              help='Generate correlation report (needs 2+ STDFs in CSV)')
    p.add_argument('files', nargs='+', help='CSV file(s) containing 2+ STDF data')
    p.add_argument('-o', '--output', help='Output xlsx path')
    p.add_argument('--cherry-pick', help='Site numbers to pick, one per file')
    p.set_defaults(func=cmd_correlation)

    # --- s2s ---
    p = subparsers.add_parser('s2s', help='Generate site-to-site correlation report')
    p.add_argument('files', nargs='+', help='CSV file(s) to analyze')
    p.add_argument('-o', '--output', help='Output xlsx path')
    p.add_argument('--cherry-pick', help='Site numbers to pick, one per file')
    p.set_defaults(func=cmd_s2s)

    # --- pdf ---
    p = subparsers.add_parser('pdf', help='Generate PDF charts for selected tests')
    p.add_argument('files', nargs='+', help='CSV file(s) to analyze')
    p.add_argument('-o', '--output', help='Output PDF path')
    p.add_argument('--tests', nargs='+', help='Specific test names to include')
    p.add_argument('--regex', help='Regex pattern to match test names')
    p.add_argument('--all', action='store_true', help='Include all tests')
    p.add_argument('--no-limits', action='store_true', help="Don't plot failure limits")
    p.add_argument('--group-by-file', action='store_true', help='Group trends by file')
    p.add_argument('--cherry-pick', help='Site numbers to pick, one per file')
    p.set_defaults(func=cmd_pdf)

    # --- extract-tests ---
    p = subparsers.add_parser('extract-tests', help='Extract sub-CSV for specific tests')
    p.add_argument('files', nargs='+', help='CSV file(s) to extract from')
    p.add_argument('-o', '--output', help='Output CSV path')
    p.add_argument('--tests', nargs='+', help='Specific test names to extract')
    p.add_argument('--regex', help='Regex pattern to match test names')
    p.add_argument('--cherry-pick', help='Site numbers to pick, one per file')
    p.set_defaults(func=cmd_extract_tests)

    # --- list-tests ---
    p = subparsers.add_parser('list-tests', help='List all test instances in a CSV file')
    p.add_argument('files', nargs='+', help='CSV file(s) to inspect')
    p.add_argument('--filter', help='Regex pattern to filter test names')
    p.add_argument('--cherry-pick', help='Site numbers to pick, one per file')
    p.set_defaults(func=cmd_list_tests)

    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Set up logging
    logging.basicConfig(
        filename=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.log'),
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s')

    print(f"\n  STDF Reader CLI")
    print(f"  {'─' * 50}")

    try:
        return args.func(args)
    except Exception as e:
        print(f"\n  ✗ Error: {e}", file=sys.stderr)
        logging.error(f"CLI error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main() or 0)
