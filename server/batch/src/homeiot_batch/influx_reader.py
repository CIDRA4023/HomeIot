"""InfluxDBから対象期間のデータを読み取る。"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from influxdb import InfluxDBClient
from requests import Session

from .config import Config


def calculate_target_window(
    config: Config, *, target_date: date | None = None
) -> tuple[date, datetime, datetime]:
    """JSTの前日（または指定日）を基準に抽出対象のUTC時間帯を返す。"""
    if target_date is None:
        now_jst = datetime.now(timezone.utc).astimezone(config.tzinfo)
        target_date = (now_jst - timedelta(days=1)).date()
    start_jst = datetime.combine(target_date, time(), tzinfo=config.tzinfo)
    end_jst = start_jst + timedelta(days=1)
    start_utc = start_jst.astimezone(timezone.utc)
    end_utc = end_jst.astimezone(timezone.utc)
    return target_date, start_utc, end_utc


def fetch_points(config: Config, start_utc: datetime, end_utc: datetime) -> list[dict[str, Any]]:
    """InfluxDBから指定期間のポイントを取得する。"""
    start_iso = start_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = end_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    query = (
        "SELECT power_w, instant_power_w, energy_import_kwh, energy_export_kwh "
        f"FROM {config.measurement} "
        f"WHERE time >= '{start_iso}' AND time < '{end_iso}'"
    )

    session = None
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
        result = client.query(query)
        return list(result.get_points())
    finally:
        client.close()
        if session:
            session.close()
