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

    client = mqtt.Client(protocol=mqtt.MQTTv5)

    if parsed.username or parsed.password:
        client.username_pw_set(parsed.username, parsed.password or None)

    client.connect(host, port)
    client.loop_start()
    print(f"MQTT 接続に成功: {host}:{port} トピック {MQTT_TOPIC}")
    return client


def main():
    mqtt_client = build_mqtt_client()

    # momongaでスマートメーターに接続
    with momonga.Momonga(rbid, pwd, dev) as mo:
        while True:
            try:
                power = mo.get_instantaneous_power()  # W
                print(f"現在の瞬時電力: {power:.1f} W")

                if mqtt_client:
                    payload = {
                        "meter": "home",
                        "power_w": float(power),
                    }
                    mqtt_client.publish(MQTT_TOPIC, json.dumps(payload), qos=1)

                # 30〜60秒くらいがオススメ
                time.sleep(10)

            except Exception as e:
                print("エラーが発生しました:", e)
                # 少し待って再トライ
                time.sleep(10)


if __name__ == "__main__":
    main()
