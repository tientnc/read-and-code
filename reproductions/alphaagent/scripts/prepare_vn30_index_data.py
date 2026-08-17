#!/usr/bin/env python3
"""Normalize a VN30 index historical CSV for Qlib ingestion.

This handles the Investing.com-style VN30 index CSV with columns:
Date, Price, Open, High, Low, Vol., Change %.

It creates one normalized daily CSV for the benchmark/index symbol VN30.
This is not enough for cross-sectional factor mining; that still requires
OHLCV histories for the VN30 constituent stocks.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_INPUT = Path("VN 30 Historical Data.csv")
DEFAULT_OUTPUT_DIR = Path("git_ignore_folder/vn_raw/index")


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


def normalize_vn30_index(input_csv: Path, output_dir: Path, symbol: str) -> Path:
    raw = pd.read_csv(input_csv, encoding="utf-8-sig")
    required = {"Date", "Price", "Open", "High", "Low", "Vol.", "Change %"}
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    out = pd.DataFrame(
        {
            "date": pd.to_datetime(raw["Date"], format="%m/%d/%Y").dt.strftime("%Y-%m-%d"),
            "symbol": symbol.upper(),
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
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--symbol", default="VN30")
    args = parser.parse_args()

    output_path = normalize_vn30_index(args.input, args.output_dir, args.symbol)
    df = pd.read_csv(output_path)
    print(f"Wrote {output_path}")
    print(f"Rows: {len(df)}")
    print(f"Date range: {df['date'].min()} -> {df['date'].max()}")
    print("Note: this is benchmark/index data only, not VN30 constituent stock data.")


if __name__ == "__main__":
    main()
