"""ParquetをソースにDuckDBへ書き込むモジュール。"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from dataclasses import dataclass
import logging

import duckdb

from .config import Config

logger = logging.getLogger(__name__)

DDL = """
CREATE TABLE IF NOT EXISTS raw_meter_readings (
  ts_utc TIMESTAMP,
  ts_jst TIMESTAMP,
  source VARCHAR,
  instant_power_w DOUBLE,
  energy_import_kwh DOUBLE,
  energy_export_kwh DOUBLE,
  ingested_at TIMESTAMP
);
"""


def _ensure_table(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute(DDL)


def _delete_target_date(connection: duckdb.DuckDBPyConnection, target_date: date) -> int | None:
    # DuckDB 1.x では DATE() 関数が無いのでキャストで日付比較する
    cursor = connection.execute(
        "DELETE FROM raw_meter_readings WHERE CAST(ts_jst AS DATE) = ?",
        [target_date],
    )
    return cursor.rowcount if cursor.rowcount != -1 else None


def _insert_from_parquet(
    connection: duckdb.DuckDBPyConnection,
    partition_dir: Path,
) -> None:
    parquet_glob = partition_dir.joinpath("*.parquet").as_posix()
    connection.execute(
        """
        INSERT INTO raw_meter_readings (
            ts_utc, ts_jst, source, instant_power_w,
            energy_import_kwh, energy_export_kwh, ingested_at
        )
        SELECT ts_utc, ts_jst, source, instant_power_w,
               energy_import_kwh, energy_export_kwh, ingested_at
        FROM read_parquet(?)
        """,
        [parquet_glob],
    )


def _count_for_date(connection: duckdb.DuckDBPyConnection, target_date: date) -> int:
    return connection.execute(
        "SELECT COUNT(*) FROM raw_meter_readings WHERE CAST(ts_jst AS DATE) = ?",
        [target_date],
    ).fetchone()[0]


def _integrity_check(connection: duckdb.DuckDBPyConnection) -> None:
    try:
        rows = connection.execute("PRAGMA integrity_check").fetchall()
    except duckdb.CatalogException:
        connection.execute("PRAGMA force_checkpoint")
        logger.warning("DuckDB integrity_check is not supported; force_checkpoint only.")
        return
    if not rows:
        raise RuntimeError("DuckDB integrity_check returned no rows")
    if len(rows) == 1 and rows[0][0] == "ok":
        return
    details = ", ".join(str(row[0]) for row in rows)
    raise RuntimeError(f"DuckDB integrity_check failed: {details}")


@dataclass
class DuckDBWriteResult:
    deleted_rows: int | None
    inserted_rows: int


def write_archive(
    config: Config,
    target_date: date,
    partition_dir: Path,
    duckdb_path: Path | None = None,
) -> DuckDBWriteResult:
    duckdb_path = duckdb_path or Path(config.duckdb_path)
    if not partition_dir.exists():
        raise FileNotFoundError(f"Parquetパーティションが見つかりません: {partition_dir}")
    duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(duckdb_path.as_posix()) as connection:
        _ensure_table(connection)
        deleted = _delete_target_date(connection, target_date)
        _insert_from_parquet(connection, partition_dir)
        inserted = _count_for_date(connection, target_date)
        connection.commit()
        connection.execute("CHECKPOINT")
        _integrity_check(connection)
    return DuckDBWriteResult(deleted_rows=deleted, inserted_rows=inserted)
