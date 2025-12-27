import json
import logging
import os
import time
from logging.handlers import RotatingFileHandler
from urllib.parse import urlparse

import momonga
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_PATH = os.path.join(LOG_DIR, "device.log")
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("homeiot_device_raspi")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        file_handler = RotatingFileHandler(
            LOG_PATH, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError as exc:
        logger.warning("ログファイルを作成できませんでした: %s", exc)

    return logger


logger = setup_logging()

# ==== スマートメーター設定 ====
rbid = os.getenv("RBID")
pwd = os.getenv("B_ROUTE_PWD")
dev = os.getenv("DEVICE")

# ==== MQTT設定 ====
MQTT_BROKER_URL = os.getenv("MQTT_BROKER_URL")
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "home/power")
MQTT_TLS_CA_CERT = os.getenv("MQTT_TLS_CA_CERT")


def validate_required_env() -> None:
    missing = []
    if not rbid:
        missing.append("RBID")
    if not pwd:
        missing.append("B_ROUTE_PWD")
    if not dev:
        missing.append("DEVICE")

    if missing:
        missing_str = ", ".join(missing)
        logger.error("必須環境変数が未設定です: %s", missing_str)
        raise SystemExit(
            f"必須環境変数が未設定です: {missing_str} (.env を確認してください)"
        )


def build_mqtt_client() -> mqtt.Client | None:
    """環境変数が揃っていれば MQTT クライアントを組み立てて接続する。"""

    if not MQTT_BROKER_URL:
        logger.warning("MQTT_BROKER_URL が未設定のため MQTT 送信をスキップします。")
        return None

    parsed = urlparse(MQTT_BROKER_URL)
    if not parsed.hostname:
        logger.error("MQTT_BROKER_URL のホストが不正です: %s", MQTT_BROKER_URL)
        return None

    host = parsed.hostname
    if parsed.scheme in ("mqtts", "ssl", "tls"):
        port = parsed.port or 8883
    else:
        port = parsed.port or 1883

    client = mqtt.Client(
        protocol=mqtt.MQTTv5,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )

    def to_reason_code(reason_code: object) -> int:
        if hasattr(reason_code, "value"):
            try:
                return int(getattr(reason_code, "value"))
            except (TypeError, ValueError):
                return -1
        try:
            return int(reason_code)
        except (TypeError, ValueError):
            return -1

    def on_connect(
        _client: mqtt.Client,
        _userdata: object,
        _flags: object,
        reason_code: object,
        _properties: object | None,
    ) -> None:
        code = to_reason_code(reason_code)
        if code == 0:
            logger.info("MQTT 接続に成功: %s:%s トピック %s", host, port, MQTT_TOPIC)
        else:
            logger.error("MQTT 接続に失敗しました: reason=%s", code)

    def on_disconnect(
        _client: mqtt.Client,
        _userdata: object,
        reason_code: object,
        _properties: object | None,
    ) -> None:
        code = to_reason_code(reason_code)
        if code != 0:
            logger.warning(
                "MQTT 切断を検知しました: reason=%s (再接続を試行します)", code
            )
        else:
            logger.info("MQTT 接続を終了しました。")

    if parsed.username or parsed.password:
        client.username_pw_set(parsed.username, parsed.password or None)

    if parsed.scheme in ("mqtts", "ssl", "tls"):
        tls_kwargs: dict[str, str] = {}
        if MQTT_TLS_CA_CERT:
            tls_kwargs["ca_certs"] = MQTT_TLS_CA_CERT
        client.tls_set(**tls_kwargs)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.reconnect_delay_set(min_delay=1, max_delay=60)

    client.connect_async(host, port)
    client.loop_start()
    return client


def main():
    validate_required_env()
    mqtt_client = build_mqtt_client()

    try:
        # momongaでスマートメーターに接続
        with momonga.Momonga(rbid, pwd, dev) as mo:
            while True:
                try:
                    power = mo.get_instantaneous_power()  # W
                    logger.info("現在の瞬時電力: %.1f W", power)
                    # 積算電力量（買電）のみ取得。取得できなくても計測は継続する。
                    energy_import = None
                    try:
                        energy_import = mo.get_measured_cumulative_energy(reverse=False)
                    except Exception as e:
                        logger.warning(
                            "積算電力量の取得に失敗しました: %s", e, exc_info=True
                        )

                    if mqtt_client:
                        payload = {
                            "meter": "home",
                            "power_w": float(power),
                            "energy_wh_import": energy_import,
                        }
                        mqtt_client.publish(MQTT_TOPIC, json.dumps(payload), qos=1)

                    # 30〜60秒くらいがオススメ
                    time.sleep(10)

                except Exception as e:
                    logger.exception("エラーが発生しました: %s", e)
                    # 少し待って再トライ
                    time.sleep(10)
    except KeyboardInterrupt:
        logger.info("終了要求を受け取りました。")
    finally:
        if mqtt_client:
            mqtt_client.disconnect()
            mqtt_client.loop_stop()


if __name__ == "__main__":
    main()
