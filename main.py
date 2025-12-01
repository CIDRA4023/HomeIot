import time
import momonga
from influxdb_client import InfluxDBClient, Point, WriteOptions
from influxdb_client.client.write_api import SYNCHRONOUS
from dotenv import load_dotenv
import os

load_dotenv()

# ==== スマートメーター設定 ====
rbid = os.getenv("RBID")
pwd = os.getenv("PWD")
dev = os.getenv("DEVICE")

# ==== InfluxDB設定 ====
INFLUX_URL = os.getenv("INFLUX_URL")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET")

# ==== InfluxDBクライアント ====
client = InfluxDBClient(
    url=INFLUX_URL,
    token=INFLUX_TOKEN,
    org=INFLUX_ORG,
)
write_api = client.write_api(write_options=SYNCHRONOUS)


def main():
    # momongaでスマートメーターに接続
    with momonga.Momonga(rbid, pwd, dev) as mo:
        while True:
            try:
                power = mo.get_instantaneous_power()  # W
                print(f"現在の瞬時電力: {power:.1f} W")

                point = (
                    Point("tepco_power")  # 測定名（measurement）
                    .tag("meter", "home")  # 複数メーター対応するならタグで切り分け
                    .field("power_w", float(power))  # フィールド名
                )

                write_api.write(
                    bucket=INFLUX_BUCKET,
                    org=INFLUX_ORG,
                    record=point,
                )

                # 30〜60秒くらいがオススメ
                time.sleep(5)

            except Exception as e:
                print("エラーが発生しました:", e)
                # 少し待って再トライ
                time.sleep(10)


if __name__ == "__main__":
    main()
