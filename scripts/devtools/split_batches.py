#!/usr/bin/env python3
"""Split a CSV file into fixed-size batch CSVs."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[2]
    default_input = repo_root / "data" / "processed" / "input_for_gemini.csv"
    default_output = repo_root / "data" / "processed" / "input_batches"

    parser = argparse.ArgumentParser(description="Split CSV into batch CSV files.")
    parser.add_argument("--input-file", default=str(default_input), help="Input CSV path.")
    parser.add_argument("--output-dir", default=str(default_output), help="Output directory for batch CSVs.")
    parser.add_argument("--batch-size", type=int, default=10, help="Rows per batch.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    input_file = Path(args.input_file)
    output_dir = Path(args.output_dir)
    batch_size = int(args.batch_size)

    if batch_size <= 0:
        raise ValueError("--batch-size must be > 0")
    if not input_file.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_file}")

    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_file)
    total_rows = len(df)
    print(f"Total rows in original file: {total_rows}")

    for i in range(0, total_rows, batch_size):
        batch_df = df.iloc[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        output_filename = output_dir / f"batch_{batch_num:03d}.csv"
        batch_df.to_csv(output_filename, index=False)
        print(f"Saved {output_filename}")

    print("Splitting complete.")


if __name__ == "__main__":
    main()
