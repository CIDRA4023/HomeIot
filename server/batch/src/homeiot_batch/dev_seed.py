"""InfluxDB にサンプルデータを書き込む開発用スクリプト。"""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, List

from influxdb import InfluxDBClient
from requests import Session

from .config import Config

logger = logging.getLogger(__name__)


def _build_points(
    *,
    start_utc: datetime,
    interval_minutes: int,
    count: int,
    measurement: str,
    source: str,
) -> List[dict[str, Any]]:
    points: List[dict[str, Any]] = []
    energy_import = 0.0
    for i in range(count):
        ts = start_utc + timedelta(minutes=interval_minutes * i)
        instant_power = 400.0 + (i % 5) * 20.0
        energy_import += instant_power * interval_minutes / 60_000.0  # kWh換算
        points.append(
            {
                "measurement": measurement,
                "time": ts.isoformat().replace("+00:00", "Z"),
                "tags": {"source": source},
                "fields": {
                    "instant_power_w": instant_power,
                    "energy_import_kwh": round(energy_import, 5),
                    "energy_export_kwh": 0.0,
                },
            }
        )
    return points


def _write_points(config: Config, points: Iterable[dict[str, Any]]) -> None:
    session: Session | None = None
    if config.influx_token:
        session = Session()
        session.headers.update({"Authorization": f"Token {config.influx_token}"})
    client = InfluxDBClient(
        host=config.influx_host,
        port=config.influx_port,
        username=config.influx_user,
        password=config.influx_password,
        database=config.influx_db,
        ssl=config.use_https,
        session=session,
    )
    try:
        success = client.write_points(list(points))
        if not success:
            raise RuntimeError("InfluxDBへの書き込みに失敗しました")
    finally:
        client.close()
        if session:
            session.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="開発用: サンプルデータを InfluxDB に投入する")
    parser.add_argument(
        "--start-utc",
        default="2025-12-16T15:00:00Z",
        help="開始UTC日時 (ISO8601, デフォルト: 2025-12-16T15:00:00Z)",
    )
    parser.add_argument(
        "--interval-minutes",
        type=int,
        default=60,
        help="サンプル間隔（分）",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=6,
        help="生成するポイント数",
    )
    parser.add_argument(
        "--source",
        default=None,
        help="sourceタグ（未指定ならSOURCE_DEFAULTを使用）",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args()
    config = Config.load()
    start_utc = datetime.fromisoformat(args.start_utc.replace("Z", "+00:00")).astimezone(timezone.utc)
    source = args.source or config.source_default

    points = _build_points(
        start_utc=start_utc,
        interval_minutes=args.interval_minutes,
        count=args.count,
        measurement=config.measurement,
        source=source,
    )
    logger.info("投入件数: %d (期間: %s 〜 %s)", len(points), points[0]["time"], points[-1]["time"])
    _write_points(config, points)
    logger.info("InfluxDB への投入が完了しました")


if __name__ == "__main__":
    main()
