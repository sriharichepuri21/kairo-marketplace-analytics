"""
Parquet writer utilities for the generator.

Converts Pydantic models to Polars DataFrames and writes them
to partitioned Parquet files in raw_data/.
"""

from pathlib import Path
from typing import Sequence

import polars as pl
from pydantic import BaseModel


def models_to_dataframe(models: Sequence[BaseModel]) -> pl.DataFrame:
    """
    Convert a list of Pydantic models to a Polars DataFrame.

    Uses model_dump() (Python mode) to preserve native Python types
    like date and datetime, so Polars can infer proper column types
    (Date, Datetime) instead of falling back to strings.

    Enum values become their .value string automatically because
    our enums inherit from str.
    """
    rows = [m.model_dump() for m in models]
    return pl.DataFrame(rows)


def write_parquet(
    df: pl.DataFrame,
    output_path: Path,
    compression: str = "zstd",
) -> None:
    """
    Write a DataFrame to a Parquet file.

    Creates parent directories if they don't exist.
    Uses Zstandard compression by default — good balance of speed and size.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(output_path, compression=compression)


def write_entities_to_parquet(
    entities: Sequence[BaseModel],
    output_path: Path,
) -> pl.DataFrame:
    """
    High-level function: take a list of Pydantic models, convert
    them to a DataFrame, and write them to a Parquet file.

    Returns the DataFrame so callers can inspect or query it.
    """
    df = models_to_dataframe(entities)
    write_parquet(df, output_path)
    return df