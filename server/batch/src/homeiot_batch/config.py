"""Environment configuration for the batch job."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo


@dataclass
class Config:
    influx_url: str
    influx_host: str
    influx_port: int
    influx_db: str
    influx_token: str | None
    influx_user: str | None
    influx_password: str | None
    duckdb_path: str
    parquet_base_dir: str
    parquet_compression: str
    parquet_row_group_size: int | None
    tz: str
    measurement: str
    source_default: str

    @property
    def tzinfo(self) -> ZoneInfo:
        return ZoneInfo(self.tz)

    @property
    def use_https(self) -> bool:
        return self.influx_url.startswith("https")

    @classmethod
    def load(cls) -> "Config":
        influx_url = os.environ.get("INFLUX_URL", "http://influxdb:8086")
        parsed_url = urlsplit(influx_url)
        return cls(
            influx_url=influx_url,
            influx_host=parsed_url.hostname or "influxdb",
            influx_port=parsed_url.port or (443 if parsed_url.scheme == "https" else 8086),
            influx_db=os.environ.get("INFLUX_BUCKET") or os.environ.get("INFLUX_DB", "home_energy"),
            influx_token=os.environ.get("INFLUX_TOKEN") or None,
            influx_user=(
                os.environ.get("INFLUX_USERNAME")
                or os.environ.get("INFLUX_USER")
                or None
            ),
            influx_password=os.environ.get("INFLUX_PASSWORD") or None,
            duckdb_path=os.environ.get("DUCKDB_PATH", "/data/duckdb/home_energy.duckdb"),
            parquet_base_dir=os.environ.get("PARQUET_BASE_DIR", "/data/parquet"),
            parquet_compression=os.environ.get("PARQUET_COMPRESSION", "zstd"),
            parquet_row_group_size=int(os.environ["PARQUET_ROW_GROUP_SIZE"])
            if "PARQUET_ROW_GROUP_SIZE" in os.environ
            else None,
            tz=os.environ.get("TZ", "Asia/Tokyo"),
            measurement=os.environ.get("INFLUX_MEASUREMENT") or os.environ.get("MEASUREMENT", "power"),
            source_default=os.environ.get("SOURCE_DEFAULT", "meter1"),
        )
