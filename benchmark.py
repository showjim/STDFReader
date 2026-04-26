"""
Benchmark script: Compare pure Python vs Cython-compiled STDF parsing performance.

Usage:
    python benchmark.py              # Run pure Python baseline
    python benchmark.py --cython     # Run after Cython compilation
"""

import os
import sys
import time
import glob
import argparse
import cProfile
import pstats
import io as sysio


def get_stdf_files():
    """Find all sample STDF files for benchmarking."""
    patterns = [
        "sample_stdf/*.std",
        "sample_stdf/*.stdf",
    ]
    files = []
    for pat in patterns:
        files.extend(glob.glob(pat, recursive=True))
    # Deduplicate and sort by size
    files = sorted(set(files), key=lambda f: os.path.getsize(f))
    return files


def benchmark_parse_only(filepath):
    """Benchmark raw STDF parsing (no CSV/Excel output)."""
    from pystdf.IO import Parser

    class NullSink:
        """Sink that discards all records - measures pure parsing speed."""
        def __init__(self):
            self.record_count = 0
        def __call__(self, dataset):
            self.record_count += 1

    sink = NullSink()

    with open(filepath, 'rb') as f:
        p = Parser(inp=f)
        p.addSink(sink)

        start = time.perf_counter()
        p.parse()
        elapsed = time.perf_counter() - start

    file_size = os.path.getsize(filepath)
    return elapsed, sink.record_count, file_size


def benchmark_to_dataframe(filepath):
    """Benchmark STDF parsing into DataFrame (typical user workflow)."""
    from pystdf.IO import Parser
    from pystdf.Importer import STDF2DataFrame

    with open(filepath, 'rb') as f:
        p = Parser(inp=f)
        sink = STDF2DataFrame()
        p.addSink(sink)

        start = time.perf_counter()
        p.parse()
        elapsed = time.perf_counter() - start

    return elapsed


def profile_parse(filepath):
    """Profile the parsing to find hotspots."""
    from pystdf.IO import Parser

    class NullSink:
        def __call__(self, dataset): pass

    pr = cProfile.Profile()
    pr.enable()

    with open(filepath, 'rb') as f:
        p = Parser(inp=f)
        p.addSink(NullSink())
        p.parse()

    pr.disable()

    # Get top 20 functions by cumulative time
    s = sysio.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats(30)
    return s.getvalue()


def format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def format_speed(size_bytes, elapsed):
    if elapsed == 0:
        return "N/A"
    speed = size_bytes / elapsed
    if speed < 1024 * 1024:
        return f"{speed / 1024:.1f} KB/s"
    else:
        return f"{speed / (1024 * 1024):.1f} MB/s"


def main():
    parser = argparse.ArgumentParser(description="STDF Reader Performance Benchmark")
    parser.add_argument("--profile", action="store_true", help="Run cProfile on largest file")
    parser.add_argument("--repeat", type=int, default=3, help="Number of repeat runs (default: 3)")
    parser.add_argument("--file", type=str, help="Benchmark a specific file only")
    args = parser.parse_args()

    # Check if Cython modules are compiled
    from pystdf import IO
    io_file = IO.__file__
    is_cython = io_file.endswith(('.pyd', '.so'))

    mode = "Cython-compiled" if is_cython else "Pure Python"
    print(f"=" * 70)
    print(f"STDF Reader Benchmark - {mode}")
    print(f"IO module: {io_file}")
    print(f"Repeats: {args.repeat}")
    print(f"=" * 70)

    if args.file:
        files = [args.file]
    else:
        files = get_stdf_files()

    if not files:
        print("No STDF files found! Place .std/.stdf files in sample_stdf/ or project/")
        sys.exit(1)

    print(f"\nFound {len(files)} STDF file(s):\n")

    # --- Benchmark: Parse Only ---
    print(f"{'File':<50} {'Size':>10} {'Records':>10} {'Time(s)':>10} {'Speed':>12}")
    print("-" * 92)

    total_bytes = 0
    total_time = 0
    total_records = 0

    for filepath in files:
        best_time = float('inf')
        records = 0
        file_size = 0

        for run in range(args.repeat):
            elapsed, rec_count, fsize = benchmark_parse_only(filepath)
            if elapsed < best_time:
                best_time = elapsed
                records = rec_count
                file_size = fsize

        total_bytes += file_size
        total_time += best_time
        total_records += records

        fname = os.path.basename(filepath)
        if len(fname) > 48:
            fname = fname[:45] + "..."
        print(f"{fname:<50} {format_size(file_size):>10} {records:>10} {best_time:>10.4f} {format_speed(file_size, best_time):>12}")

    print("-" * 92)
    print(f"{'TOTAL':<50} {format_size(total_bytes):>10} {total_records:>10} {total_time:>10.4f} {format_speed(total_bytes, total_time):>12}")

    # --- Benchmark: DataFrame conversion (on largest file) ---
    largest_file = files[-1]
    print(f"\n{'=' * 70}")
    print(f"DataFrame Conversion Benchmark (largest file)")
    print(f"File: {os.path.basename(largest_file)}")
    print(f"{'=' * 70}")

    df_times = []
    for run in range(args.repeat):
        try:
            elapsed = benchmark_to_dataframe(largest_file)
            df_times.append(elapsed)
            print(f"  Run {run + 1}: {elapsed:.4f}s")
        except Exception as e:
            print(f"  Run {run + 1}: FAILED - {e}")

    if df_times:
        best = min(df_times)
        avg = sum(df_times) / len(df_times)
        print(f"  Best: {best:.4f}s  Avg: {avg:.4f}s")

    # --- Profile ---
    if args.profile:
        print(f"\n{'=' * 70}")
        print(f"cProfile Results (largest file: {os.path.basename(largest_file)})")
        print(f"{'=' * 70}")
        print(profile_parse(largest_file))

    # Summary
    print(f"\n{'=' * 70}")
    print(f"Summary: {mode}")
    print(f"  Total parse time: {total_time:.4f}s")
    print(f"  Total records:    {total_records}")
    print(f"  Throughput:       {format_speed(total_bytes, total_time)}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
