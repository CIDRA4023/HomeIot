"""InfluxDB→DuckDBの日次アーカイブを実行するエントリポイント。"""

from __future__ import annotations

import logging
import sys
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .config import Config
from .duckdb_writer import write_archive
from .influx_reader import calculate_target_window, fetch_points
from .parquet_writer import write_parquet_dataset
from .transform import transform_points

logger = logging.getLogger(__name__)


def _wal_path(duckdb_path: Path) -> Path:
    return Path(f"{duckdb_path.as_posix()}.wal")


def _next_duckdb_path(duckdb_path: Path) -> Path:
    if duckdb_path.suffix == ".duckdb":
        return duckdb_path.with_name(f"{duckdb_path.stem}.next{duckdb_path.suffix}")
    return duckdb_path.with_name(f"{duckdb_path.name}.next")


def _prev_duckdb_path(duckdb_path: Path) -> Path:
    if duckdb_path.suffix == ".duckdb":
        return duckdb_path.with_name(f"{duckdb_path.stem}.prev{duckdb_path.suffix}")
    return duckdb_path.with_name(f"{duckdb_path.name}.prev")


def _remove_if_exists(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return


def _prepare_duckdb_copy(base_path: Path, next_path: Path) -> None:
    next_path.parent.mkdir(parents=True, exist_ok=True)
    _remove_if_exists(next_path)
    _remove_if_exists(_wal_path(next_path))
    if base_path.exists():
        shutil.copy2(base_path, next_path)
        base_wal = _wal_path(base_path)
        if base_wal.exists():
            shutil.copy2(base_wal, _wal_path(next_path))


def _swap_duckdb_files(base_path: Path, next_path: Path) -> Path | None:
    prev_path = _prev_duckdb_path(base_path)
    if base_path.exists():
        _remove_if_exists(prev_path)
        _remove_if_exists(_wal_path(prev_path))
        os.replace(base_path, prev_path)
        base_wal = _wal_path(base_path)
        if base_wal.exists():
            os.replace(base_wal, _wal_path(prev_path))
    os.replace(next_path, base_path)
    next_wal = _wal_path(next_path)
    if next_wal.exists():
        os.replace(next_wal, _wal_path(base_path))
    return prev_path if prev_path.exists() else None


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config = Config.load()

    try:
        target_date, start_utc, end_utc = calculate_target_window(config)
        logger.info("ターゲット日 (JST): %s / 期間UTC: %s 〜 %s", target_date, start_utc, end_utc)

        points = fetch_points(config, start_utc, end_utc)
        logger.info("抽出件数: %d", len(points))

        ingested_at = datetime.now(timezone.utc)
        rows = transform_points(
            points,
            source_default=config.source_default,
            tzinfo=config.tzinfo,
            ingested_at=ingested_at,
        )

        partition_dir = write_parquet_dataset(config, target_date, rows)
        logger.info("Parquet出力先: %s", partition_dir)

        duckdb_path = Path(config.duckdb_path)
        next_duckdb_path = _next_duckdb_path(duckdb_path)
        _prepare_duckdb_copy(duckdb_path, next_duckdb_path)
        result = write_archive(
            config,
            target_date,
            partition_dir,
            duckdb_path=next_duckdb_path,
        )
        prev_path = _swap_duckdb_files(duckdb_path, next_duckdb_path)
        if prev_path:
            logger.info("DuckDB退避先: %s", prev_path)
        if result.deleted_rows is not None:
            logger.info("DuckDB削除件数: %d", result.deleted_rows)
        logger.info("DuckDB挿入件数: %d", result.inserted_rows)
    except Exception:
        logger.exception("アーカイブ処理でエラーが発生しました")
        sys.exit(1)


if __name__ == "__main__":
    main()
