import time
import momonga
import json
import os
from urllib.parse import urlparse

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()

# ==== スマートメーター設定 ====
rbid = os.getenv("RBID")
pwd = os.getenv("B_ROUTE_PWD")
dev = os.getenv("DEVICE")

# ==== MQTT設定 ====
MQTT_BROKER_URL = os.getenv("MQTT_BROKER_URL")
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "home/power")


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
        raise SystemExit(
            f"必須環境変数が未設定です: {missing_str} (.env を確認してください)"
        )


def build_mqtt_client() -> mqtt.Client | None:
    """環境変数が揃っていれば MQTT クライアントを組み立てて接続する。"""

    if not MQTT_BROKER_URL:
        print("MQTT_BROKER_URL が未設定のため MQTT 送信をスキップします。")
        return None

    parsed = urlparse(MQTT_BROKER_URL)
    if not parsed.hostname:
        print(f"MQTT_BROKER_URL のホストが不正です: {MQTT_BROKER_URL}")
        return None

    host = parsed.hostname
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
            print(f"MQTT 接続に成功: {host}:{port} トピック {MQTT_TOPIC}")
        else:
            print(f"MQTT 接続に失敗しました: reason={code}")

    def on_disconnect(
        _client: mqtt.Client,
        _userdata: object,
        reason_code: object,
        _properties: object | None,
    ) -> None:
        code = to_reason_code(reason_code)
        if code != 0:
            print(f"MQTT 切断を検知しました: reason={code} (再接続を試行します)")
        else:
            print("MQTT 接続を終了しました。")

    if parsed.username or parsed.password:
        client.username_pw_set(parsed.username, parsed.password or None)

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
                    print(f"現在の瞬時電力: {power:.1f} W")
                    # 積算電力量（買電）のみ取得。取得できなくても計測は継続する。
                    energy_import = None
                    try:
                        energy_import = mo.get_measured_cumulative_energy(reverse=False)
                    except Exception as e:
                        print(f"積算電力量の取得に失敗しました: {e}")

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
                    print("エラーが発生しました:", e)
                    # 少し待って再トライ
                    time.sleep(10)
    except KeyboardInterrupt:
        print("終了要求を受け取りました。")
    finally:
        if mqtt_client:
            mqtt_client.disconnect()
            mqtt_client.loop_stop()


if __name__ == "__main__":
    main()
