"""InfluxDBから変換した行をParquetへ書き出す。"""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path
from typing import Sequence

import pyarrow as pa
import pyarrow.parquet as pq

from .config import Config
from .transform import Row

COLUMN_NAMES = (
    "ts_utc",
    "ts_jst",
    "source",
    "instant_power_w",
    "energy_import_kwh",
    "energy_export_kwh",
    "ingested_at",
)


def _build_schema(tz: str) -> pa.Schema:
    return pa.schema(
        [
            ("ts_utc", pa.timestamp("us", tz="UTC")),
            ("ts_jst", pa.timestamp("us", tz=tz)),
            ("source", pa.string()),
            ("instant_power_w", pa.float64()),
            ("energy_import_kwh", pa.float64()),
            ("energy_export_kwh", pa.float64()),
            ("ingested_at", pa.timestamp("us", tz="UTC")),
        ]
    )


def _prepare_partition_dirs(base_dir: str, target_date: date) -> tuple[Path, Path]:
    dataset_dir = Path(base_dir) / "raw_meter_readings"
    partition_dir = dataset_dir / f"dt={target_date.isoformat()}"
    tmp_dir = partition_dir.with_name(partition_dir.name + "__tmp__")
    return partition_dir, tmp_dir


def _write_table(path: Path, schema: pa.Schema, rows: Sequence[Row], config: Config) -> None:
    table = pa.Table.from_pylist(
        [dict(zip(COLUMN_NAMES, row)) for row in rows],
        schema=schema,
    )
    pq.write_table(
        table,
        path,
        compression=config.parquet_compression,
        row_group_size=config.parquet_row_group_size,
    )


def write_parquet_dataset(config: Config, target_date: date, rows: Sequence[Row]) -> Path:
    partition_dir, tmp_dir = _prepare_partition_dirs(config.parquet_base_dir, target_date)
    if partition_dir.exists():
        shutil.rmtree(partition_dir)
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    schema = _build_schema(config.tz)
    output_file = tmp_dir / "part-0000.parquet"
    try:
        _write_table(output_file, schema, rows, config)
        tmp_dir.rename(partition_dir)
    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise
    return partition_dir
