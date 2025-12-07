from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import paho.mqtt.client as mqtt
from fastapi import FastAPI
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS, WriteApi
from pydantic import BaseModel, Field


INFLUX_URL = os.getenv("INFLUX_URL")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET")
MQTT_BROKER_URL = os.getenv("MQTT_BROKER_URL", "mqtt://mqtt:1883")
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "home/power")

app = FastAPI(title="Home IoT Server", version="0.2.0")


class PowerReading(BaseModel):
    meter: str = Field(description="Logical meter name, e.g. 'home'")
    power_w: float = Field(description="Instantaneous power in watts")
    measured_at: Optional[datetime] = Field(
        default=None, description="UTC timestamp supplied by the device"
    )


client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api: WriteApi = client.write_api(write_options=SYNCHRONOUS)


def _write_to_influx(reading: PowerReading) -> None:
    point = (
        Point("tepco_power")
        .tag("meter", reading.meter)
        .field("power_w", float(reading.power_w))
    )
    if reading.measured_at:
        point.time(reading.measured_at)

    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)


def _build_mqtt_client() -> mqtt.Client | None:
    parsed = urlparse(MQTT_BROKER_URL)
    if not parsed.hostname:
        print(f"MQTT_BROKER_URL のホストが不正です: {MQTT_BROKER_URL}")
        return None

    host = parsed.hostname
    port = parsed.port or 1883

    mqtt_client = mqtt.Client(protocol=mqtt.MQTTv5)
    if parsed.username or parsed.password:
        mqtt_client.username_pw_set(parsed.username, parsed.password or None)

    def on_connect(client: mqtt.Client, userdata, flags, reason_code, properties=None):
        if reason_code != mqtt.ReasonCodes.SUCCESS:
            print(f"MQTT 接続に失敗: {reason_code}")
            return
        client.subscribe(MQTT_TOPIC, qos=1)
        print(f"MQTT 接続完了: {host}:{port} / topic={MQTT_TOPIC}")

    def on_message(client: mqtt.Client, userdata, message: mqtt.MQTTMessage):
        try:
            payload = json.loads(message.payload.decode("utf-8"))
            reading = PowerReading(**payload)
            _write_to_influx(reading)
            print(f"MQTT 受信 -> Influx 書き込み完了: {reading}")
        except Exception as exc:
            print(f"MQTT メッセージ処理エラー: {exc} / payload={message.payload!r}")

    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    mqtt_client.connect(host, port)
    mqtt_client.loop_start()
    return mqtt_client


mqtt_client = _build_mqtt_client()


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """ヘルスチェック用の軽量エンドポイント。"""

    return {
        "status": "ok",
        "influx_url": INFLUX_URL or "not-set",
        "mqtt_connected": bool(mqtt_client),
    }


@app.post("/readings", tags=["power"])
def ingest_reading(reading: PowerReading) -> dict[str, str]:
    """HTTP 経由の読み取りデータも InfluxDB に反映する。"""

    _write_to_influx(reading)
    return {"status": "written"}
