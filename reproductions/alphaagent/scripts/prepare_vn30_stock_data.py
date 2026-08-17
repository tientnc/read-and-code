#!/usr/bin/env python3
"""Normalize manually exported VN30 stock CSVs from Investing.com.

Investing.com historical exports use columns like:
Date, Price, Open, High, Low, Vol., Change %

Put one CSV per stock in `git_ignore_folder/vn_raw/stocks/investing/`.
The filename stem is used as the symbol, e.g. `BID.csv`, `FPT.csv`.
This script writes normalized Qlib-ready CSVs to `git_ignore_folder/vn_raw/stocks/`.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_INPUT_DIR = Path("git_ignore_folder/vn_raw/stocks/investing")
DEFAULT_OUTPUT_DIR = Path("git_ignore_folder/vn_raw/stocks")
REQUIRED_COLUMNS = {"Date", "Price", "Open", "High", "Low", "Vol.", "Change %"}

VN30_SYMBOLS = [
    "ACB", "BID", "CTG", "HDB", "MBB", "SHB", "SSB", "TCB", "TPB", "VCB", "VPB",
    "BCM", "VHM", "VIC", "VRE",
    "MSN", "MWG", "PNJ", "SAB", "VJC",
    "FPT",
    "DGC", "GAS", "GVR", "HPG", "PLX",
    "BVH", "POW", "SSI", "STB",
]


def parse_number(value: object) -> float:
    if pd.isna(value):
        return float("nan")
    text = str(value).strip().replace(",", "")
    if not text or text == "-":
        return float("nan")
    return float(text)


def parse_volume(value: object) -> float:
    if pd.isna(value):
        return float("nan")
    text = str(value).strip().replace(",", "")
    if not text or text == "-":
        return float("nan")
    multiplier = 1.0
    suffix = text[-1].upper()
    if suffix == "K":
        multiplier = 1_000.0
        text = text[:-1]
    elif suffix == "M":
        multiplier = 1_000_000.0
        text = text[:-1]
    elif suffix == "B":
        multiplier = 1_000_000_000.0
        text = text[:-1]
    return float(text) * multiplier


def parse_change(value: object) -> float:
    if pd.isna(value):
        return float("nan")
    text = str(value).strip().replace("%", "")
    if not text or text == "-":
        return float("nan")
    return float(text) / 100.0


def normalize_investing_csv(input_csv: Path, output_dir: Path, symbol: str | None = None) -> Path:
    symbol = (symbol or input_csv.stem).upper().strip()
    raw = pd.read_csv(input_csv, encoding="utf-8-sig")
    missing = REQUIRED_COLUMNS - set(raw.columns)
    if missing:
        raise ValueError(f"{input_csv} missing required columns: {sorted(missing)}")

    out = pd.DataFrame(
        {
            "date": pd.to_datetime(raw["Date"], errors="raise").dt.strftime("%Y-%m-%d"),
            "symbol": symbol,
            "open": raw["Open"].map(parse_number),
            "high": raw["High"].map(parse_number),
            "low": raw["Low"].map(parse_number),
            "close": raw["Price"].map(parse_number),
            "volume": raw["Vol."].map(parse_volume),
            "change": raw["Change %"].map(parse_change),
            "factor": 1.0,
        }
    )
    out = out.sort_values("date").drop_duplicates("date", keep="last")
    out = out.dropna(subset=["date", "open", "high", "low", "close"])

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{symbol.lower()}.csv"
    out.to_csv(output_path, index=False)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--strict-vn30", action="store_true", help="Fail if any expected VN30 symbol CSV is missing")
    args = parser.parse_args()

    if not args.input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {args.input_dir}")

    files = sorted(args.input_dir.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found in {args.input_dir}")

    written = []
    for file_path in files:
        written.append(normalize_investing_csv(file_path, args.output_dir))

    symbols = sorted(path.stem.upper() for path in written)
    missing = sorted(set(VN30_SYMBOLS) - set(symbols))
    extra = sorted(set(symbols) - set(VN30_SYMBOLS))

    print(f"Normalized {len(written)} stock CSVs into {args.output_dir}")
    print("Symbols:", ", ".join(symbols))
    if missing:
        print("Missing expected VN30 symbols:", ", ".join(missing))
    if extra:
        print("Extra symbols:", ", ".join(extra))
    if args.strict_vn30 and missing:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
