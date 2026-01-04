"""InfluxDBのポイントをDuckDBに投入する形へ変換する。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, List, Tuple
from zoneinfo import ZoneInfo

Row = Tuple[datetime, datetime, str, float, float, float, datetime]


def _parse_utc(time_value: str) -> datetime:
    ts_str = time_value.replace("Z", "+00:00")
    ts = datetime.fromisoformat(ts_str)
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def transform_point(
    point: dict[str, Any],
    *,
    source_default: str,
    tzinfo: ZoneInfo,
    ingested_at: datetime,
) -> Row:
    ts_utc = _parse_utc(point["time"])
    ts_jst = ts_utc.astimezone(tzinfo)
    source = str(point.get("source") or source_default)
    power_value = point.get("power_w")
    if power_value is None:
        power_value = point.get("instant_power_w")
    instant_power_w = float(power_value or 0.0)

    energy_import_kwh = float(point.get("energy_import_kwh") or 0.0)
    energy_export_kwh = float(point.get("energy_export_kwh") or 0.0)
    return (
        ts_utc,
        ts_jst,
        source,
        instant_power_w,
        energy_import_kwh,
        energy_export_kwh,
        ingested_at,
    )


def transform_points(
    points: Iterable[dict[str, Any]],
    *,
    source_default: str,
    tzinfo: ZoneInfo,
    ingested_at: datetime,
) -> List[Row]:
    return [
        transform_point(
            point,
            source_default=source_default,
            tzinfo=tzinfo,
            ingested_at=ingested_at,
        )
        for point in points
    ]
