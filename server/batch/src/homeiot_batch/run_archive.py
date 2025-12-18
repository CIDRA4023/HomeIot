"""InfluxDB→DuckDBの日次アーカイブを実行するエントリポイント。"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone

from .config import Config
from .duckdb_writer import write_archive
from .influx_reader import calculate_target_window, fetch_points
from .parquet_writer import write_parquet_dataset
from .transform import transform_points

logger = logging.getLogger(__name__)


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

        result = write_archive(config, target_date, partition_dir)
        if result.deleted_rows is not None:
            logger.info("DuckDB削除件数: %d", result.deleted_rows)
        logger.info("DuckDB挿入件数: %d", result.inserted_rows)
    except Exception:
        logger.exception("アーカイブ処理でエラーが発生しました")
        sys.exit(1)


if __name__ == "__main__":
    main()
