## Device (Raspberry Pi)

### Overview
Raspberry Pi Zero2 でスマートメーターを読み取り、MQTT へ publish します。

### Prerequisites
- Python 3.12+ と uv を用意する
- B ルート情報と MQTT 接続情報を用意する
- 送信先 MQTT ブローカーの TLS 設定を準備する

### Setup
```bash
cd device/raspi-zero2
cp .env.sample .env
uv sync
```

### Configuration
`.env` を編集して以下を設定します。

- `RBID`, `B_ROUTE_PWD`, `DEVICE`: momonga でスマートメーターへ接続するための B ルート情報
- `MQTT_BROKER_URL`, `MQTT_TLS_CA_CERT`, `MQTT_TOPIC`: MQTT publish 先の設定
- `UPTIME_KUMA_PUSH_URL`, `UPTIME_KUMA_PUSH_TIMEOUT`: publish 成功時の監視連携（任意）

### Run
```bash
uv run python -m homeiot_device_raspi.main
```

### Run As Service (systemd)
1) `.env` と `uv sync` が完了していることを確認し、systemd ユニットを作成します。

```bash
sudo tee /etc/systemd/system/homeiot-device.service >/dev/null <<'UNIT'
[Unit]
Description=HomeIoT Raspberry Pi Device
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/home-iot/device/raspi-zero2
EnvironmentFile=/home/pi/home-iot/device/raspi-zero2/.env
Environment=PATH=/home/pi/.local/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/pi/.local/bin/uv run python -m homeiot_device_raspi.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
UNIT
```

2) 有効化して起動します。

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now homeiot-device.service
```

### Operations
- 停止: `sudo systemctl stop homeiot-device.service`
- 自動起動停止: `sudo systemctl disable homeiot-device.service`
- ログ確認: `journalctl -u homeiot-device.service -f`

### Notes
- パスやユーザーは環境に合わせて変更してください（例: `WorkingDirectory`, `ExecStart`）。
