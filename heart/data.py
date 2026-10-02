import argparse
import urllib.request
from pathlib import Path

import pandas as pd

from heart.config import CLEAN_PATH, DATA_URL, FEATURES, RAW_COLUMNS, RAW_PATH, TARGET


# Download the raw Cleveland file from UCI unless a cached copy already exists.
def download_raw(url: str = DATA_URL, dest: Path = RAW_PATH, force: bool = False) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if force or not dest.exists():
        urllib.request.urlretrieve(url, dest)
    return dest


# Read the raw comma-separated file, naming columns and treating '?' as missing.
def load_raw(path: Path = RAW_PATH) -> pd.DataFrame:
    return pd.read_csv(path, header=None, names=RAW_COLUMNS, na_values="?")


# Coerce types, binarise the 0-4 diagnosis into a 0/1 target and drop duplicates.
def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.apply(pd.to_numeric, errors="coerce")
    df = df.dropna(subset=["num"]).drop_duplicates().reset_index(drop=True)
    df[TARGET] = (df["num"] > 0).astype(int)
    return df.drop(columns="num")


# Load the cleaned CSV, rebuilding it from the raw file when it is missing.
def load_clean(path: Path = CLEAN_PATH) -> pd.DataFrame:
    if not path.exists():
        build_clean_dataset()
    return pd.read_csv(path)


# Split a cleaned frame into the model feature matrix and the target vector.
def split_xy(df: pd.DataFrame):
    return df[FEATURES], df[TARGET]


# Run the full acquisition step: download, clean and persist the dataset.
def build_clean_dataset(force_download: bool = False) -> pd.DataFrame:
    df = clean(load_raw(download_raw(force=force_download)))
    CLEAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CLEAN_PATH, index=False)
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download and clean the UCI heart dataset")
    parser.add_argument("--force", action="store_true", help="re-download even if cached")
    args = parser.parse_args()
    data = build_clean_dataset(force_download=args.force)
    print(f"Saved {len(data)} rows to {CLEAN_PATH}")
    print("Missing values per column:")
    print(data.isna().sum()[data.isna().sum() > 0].to_string())
    print("Class balance:", data[TARGET].value_counts().to_dict())
