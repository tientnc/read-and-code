#!/usr/bin/env python3
"""Build a VN30 Qlib provider from normalized VN stock CSVs plus VN30 index CSV."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

import pandas as pd


DEFAULT_STOCK_DIR = Path("git_ignore_folder/vn_raw/stocks")
DEFAULT_INDEX_CSV = Path("git_ignore_folder/vn_raw/index/vn30.csv")
DEFAULT_FULL_DIR = Path("git_ignore_folder/vn_raw/full")
DEFAULT_QLIB_DIR = Path("qlib_data/vn_data")
DEFAULT_DUMP_SCRIPT = Path("helper_repos/qlib/scripts/dump_bin.py")
DEFAULT_PYTHON = Path(".venv/bin/python")


def copy_inputs(stock_dir: Path, index_csv: Path, full_dir: Path) -> list[Path]:
    full_dir.mkdir(parents=True, exist_ok=True)
    for old in full_dir.glob("*.csv"):
        old.unlink()

    copied = []
    for csv_path in sorted(stock_dir.glob("*.csv")):
        if csv_path.resolve() == index_csv.resolve():
            continue
        dst = full_dir / csv_path.name
        shutil.copy2(csv_path, dst)
        copied.append(dst)

    if index_csv.exists():
        dst = full_dir / "vn30.csv"
        shutil.copy2(index_csv, dst)
        copied.append(dst)
    else:
        print(f"Warning: VN30 index CSV not found: {index_csv}")
    return copied


def run_dump(python: Path, dump_script: Path, full_dir: Path, qlib_dir: Path, workers: int) -> None:
    cmd = [
        str(python),
        str(dump_script),
        "dump_all",
        "--data_path",
        str(full_dir),
        "--qlib_dir",
        str(qlib_dir),
        "--freq",
        "day",
        "--date_field_name",
        "date",
        "--include_fields",
        "open,high,low,close,volume,change,factor",
        "--max_workers",
        str(workers),
    ]
    subprocess.run(cmd, check=True)


def write_vn30_pool(stock_dir: Path, qlib_dir: Path) -> None:
    rows = []
    for csv_path in sorted(stock_dir.glob("*.csv")):
        symbol = csv_path.stem.upper()
        if symbol == "VN30":
            continue
        df = pd.read_csv(csv_path, usecols=["date"])
        rows.append((symbol, df["date"].min(), df["date"].max()))

    instruments_dir = qlib_dir / "instruments"
    instruments_dir.mkdir(parents=True, exist_ok=True)
    vn30_path = instruments_dir / "vn30.txt"
    with vn30_path.open("w") as f:
        for symbol, start, end in rows:
            f.write(f"{symbol}\t{start}\t{end}\n")


def write_index_pool(index_csv: Path, qlib_dir: Path) -> None:
    if not index_csv.exists():
        return
    df = pd.read_csv(index_csv, usecols=["date"])
    instruments_dir = qlib_dir / "instruments"
    instruments_dir.mkdir(parents=True, exist_ok=True)
    with (instruments_dir / "vn30_index.txt").open("w") as f:
        f.write(f"VN30\t{df['date'].min()}\t{df['date'].max()}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stock-dir", type=Path, default=DEFAULT_STOCK_DIR)
    parser.add_argument("--index-csv", type=Path, default=DEFAULT_INDEX_CSV)
    parser.add_argument("--full-dir", type=Path, default=DEFAULT_FULL_DIR)
    parser.add_argument("--qlib-dir", type=Path, default=DEFAULT_QLIB_DIR)
    parser.add_argument("--dump-script", type=Path, default=DEFAULT_DUMP_SCRIPT)
    parser.add_argument("--python", type=Path, default=DEFAULT_PYTHON)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    copied = copy_inputs(args.stock_dir, args.index_csv, args.full_dir)
    stock_count = len([p for p in copied if p.stem.upper() != "VN30"])
    if stock_count == 0:
        raise SystemExit(f"No normalized stock CSVs found in {args.stock_dir}")

    run_dump(args.python, args.dump_script, args.full_dir, args.qlib_dir, args.workers)
    write_vn30_pool(args.stock_dir, args.qlib_dir)
    write_index_pool(args.index_csv, args.qlib_dir)

    print(f"Built Qlib provider: {args.qlib_dir}")
    print(f"Stock count: {stock_count}")
    print(f"Tradable pool: {args.qlib_dir / 'instruments' / 'vn30.txt'}")
    print(f"Benchmark pool: {args.qlib_dir / 'instruments' / 'vn30_index.txt'}")


if __name__ == "__main__":
    main()
