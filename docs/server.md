## Server (HomeServer)

### Overview
MQTT ブローカー、mqtt_gateway、InfluxDB、Grafana を Docker Compose で運用するための手順です。

### Prerequisites
- Cloudflare アカウントとドメインが準備済み
- Cloudflare Tunnel を作成済み（トークン方式）
- DNS で `grafana.example.com` / `app.example.com` を Tunnel に向ける
- MQTT の接続先ホスト名/IP を決めておく（証明書の SAN と一致が必須）

### Environment Setup
`server/.env.sample` をルート直下の `.env` にコピーして編集します。

```bash
cp server/.env.sample .env
```

#### Environment Variables
`server/.env.sample` に含まれる変数の概要です。用途ごとに並べています。

App:
- `APP_PORT` (required): `app` コンテナが待ち受けるポート。`docker-compose.yml` の公開ポートと合わせます。

InfluxDB bootstrap:
- `DOCKER_INFLUXDB_INIT_MODE` (required): 初回セットアップのモード。通常は `setup`。
- `DOCKER_INFLUXDB_INIT_USERNAME` (required): 初期管理ユーザー名。
- `DOCKER_INFLUXDB_INIT_PASSWORD` (required): 初期管理パスワード。
- `DOCKER_INFLUXDB_INIT_ORG` (required): 初期 Org 名。
- `DOCKER_INFLUXDB_INIT_BUCKET` (required): 初期 Bucket 名。
- `DOCKER_INFLUXDB_INIT_ADMIN_TOKEN` (required): 初期管理トークン。`INFLUX_TOKEN` と一致させます。

Application defaults:
- `INFLUX_URL` (required): mqtt_gateway が接続する InfluxDB URL。  例: `http://influxdb:8086`
- `INFLUX_TOKEN` (required): InfluxDB のアクセストークン。`DOCKER_INFLUXDB_INIT_ADMIN_TOKEN` と一致させます。
- `INFLUX_ORG` (required): InfluxDB の Org 名。`DOCKER_INFLUXDB_INIT_ORG` と一致させます。
- `INFLUX_BUCKET` (required): InfluxDB の Bucket 名。`DOCKER_INFLUXDB_INIT_BUCKET` と一致させます。
- `INFLUX_MEASUREMENT` (required): InfluxDB に書き込む measurement 名。

Batch defaults:
- `DUCKDB_PATH` (required): バッチが書き込む DuckDB のパス。  例: `/data/duckdb/home_energy.duckdb`
- `SOURCE_DEFAULT` (required): バッチ用の source タグの既定値。
- `TZ` (required): バッチ実行時のタイムゾーン。JST を想定するなら `Asia/Tokyo`。

MQTT broker:
- `MQTT_BROKER_URL` (required): mqtt_gateway が接続する MQTT エンドポイント。\n  例: `mqtts://homeiot:change-me@mqtt.example.com:8883`
- `MQTT_TOPIC` (required): デバイスが publish するトピック。\n  例: `home/power`
- `MQTT_USER` (required): Mosquitto のユーザー名。`passwords` の生成時と一致させます。
- `MQTT_PASSWORD` (required): Mosquitto のパスワード。`MQTT_BROKER_URL` にも同じ値を入れます。
- `MQTT_HOST` (required): MQTT ブローカーのホスト名。TLS 証明書の SAN と一致させます。
- `MQTT_TLS_CA_CERT` (required): mqtt_gateway が信頼する CA 証明書のパス。\n  `server/config/mosquitto/certs/ca.crt` を `app` へマウントしたパスに合わせます。\n  例: `/etc/ssl/certs/homeiot-ca.crt`

Cloudflare Tunnel:
- `CLOUDFLARE_TUNNEL_TOKEN` (required): Cloudflare Tunnel のトークン。`cloudflared` コンテナが使用します。\n  例: `eyJhIjoi...`（Zero Trust の Tunnel 画面で発行）

#### Notes
- `MQTT_BROKER_URL` はサーバー内の mqtt_gateway 用（TLS 接続）
- `server/config/mosquitto/certs/ca.crt` を `app` へマウントする（`/etc/ssl/certs/homeiot-ca.crt`）
- 外部公開は 8883 のみ（TLS 必須）
- ホスト名/IP は証明書の SAN と一致させる（IP 直指定する場合は SAN に IP を入れる）

### Cloudflare Tunnel (token)
トークン方式では Cloudflare 側の設定が優先されます。以下を Cloudflare Zero Trust で設定します。

- Tunnels → 対象トンネル → Public Hostnames
  - `grafana.example.com` → `http://grafana:3000`
  - `app.example.com` → `http://app:8000`（mqtt_gateway の API）

### MQTT TLS Certificates
`server/config/mosquitto/certs/README.md` の手順で `ca.crt` / `server.crt` / `server.key` を作成します。SAN 付き証明書が必須です。

DNS 名（推奨）:
```bash
cd server/config/mosquitto/certs
openssl genrsa -out server.key 2048
openssl req -new -key server.key -subj "/CN=mqtt.example.com" \
  -addext "subjectAltName=DNS:mqtt.example.com" -out server.csr
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out server.crt -days 825 -sha256 -copy_extensions copy
```

IP 直指定（ローカル検証向け）:
```bash
cd server/config/mosquitto/certs
openssl genrsa -out server.key 2048
openssl req -new -key server.key -subj "/CN=<IP>" \
  -addext "subjectAltName=IP:<IP>" -out server.csr
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out server.crt -days 825 -sha256 -copy_extensions copy
```

### Mosquitto Credentials
`passwords` はコミットしないため、生成が必要です。

```bash
docker run --rm -v "$PWD/server/config/mosquitto:/mosquitto/config" \
  eclipse-mosquitto:2.0 mosquitto_passwd -c /mosquitto/config/passwords "${MQTT_USER}"
```

ACL は `server/config/mosquitto/aclfile` を編集して調整してください。

### Run
```bash
docker compose up -d
docker compose logs -f cloudflared
```

`.env` を変更した場合は、`app` を再作成して反映します。
```bash
docker compose up -d --force-recreate app
```

運用時は `cloudflared` のイメージを固定タグにすることを推奨します。

### Raspberry Pi MQTT Example
`ca.crt` をラズパイへ配布し、`/etc/ssl/certs/homeiot-ca.crt` に配置してから設定します。

```bash
scp server/config/mosquitto/certs/ca.crt pi@raspi:/etc/ssl/certs/homeiot-ca.crt
```

```
MQTT_BROKER_URL=mqtts://homeiot:change-me@mqtt.example.com:8883
MQTT_TLS_CA_CERT=/etc/ssl/certs/homeiot-ca.crt
MQTT_TOPIC=home/power
```

IP 直指定で接続する場合は、上記のホスト名を IP に置き換え、証明書の SAN も IP に合わせます。

### Batch Archive (Influx → Parquet → DuckDB)

#### Overview
前日（JST）の電力データを InfluxDB から取り出し、`/data/parquet/raw_meter_readings/dt=YYYY-MM-DD/` に Parquet 出力した後、Parquet をソースに DuckDB `/data/duckdb/home_energy.duckdb` の `raw_meter_readings` へロードします。

#### Prerequisites
- ルートで `.env` を作成済み（`server/.env.sample` をコピーして必要な設定を調整）
- `docker compose up -d influxdb mqtt` で InfluxDB と Mosquitto を起動済み（`app` は任意）
- `docker-compose.yml` で `/data/duckdb` と `/data/parquet` がホストにマウントされる

#### Seed Sample Data (optional)
開発用に対象期間へサンプルを入れる:
```bash
docker compose run --rm batch python -m homeiot_batch.dev_seed
```

主なオプション:
- `--start-utc 2025-12-16T15:00:00Z` 開始時刻(UTC)
- `--interval-minutes 30` ポイント間隔
- `--count 24` 件数
- `--source meter1` sourceタグ（省略時は SOURCE_DEFAULT）

#### Run Daily Archive
```bash
docker compose run --rm batch python -m homeiot_batch.run_archive
```

実行内容:
1. 前日(JST)の 00:00〜24:00 を UTC に変換して InfluxDB から取得
2. Parquet を一時ディレクトリに書き出し、`dt=YYYY-MM-DD` へ原子的にリネーム
3. DuckDB は `home_energy.next.duckdb` に書き込み（対象日 DELETE → Parquet から INSERT）
4. `PRAGMA integrity_check` と `CHECKPOINT` 実行後、`home_energy.duckdb` と原子的に入れ替え（既存DBは `home_energy.prev.duckdb` に退避）

#### Verify Outputs
- Parquet: `ls data/parquet/raw_meter_readings/dt=YYYY-MM-DD`
- DuckDB 件数例: `duckdb data/duckdb/home_energy.duckdb "SELECT COUNT(*) FROM raw_meter_readings;"` （手元に duckdb コマンドがある場合）

#### Schedule (systemd timer)
`/path/to/HomeIot` は実際のリポジトリパスに置き換えてください。

`/etc/systemd/system/homeiot-batch.service`:
```ini
[Unit]
Description=HomeIot batch archive
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
WorkingDirectory=/path/to/HomeIot
ExecStart=/usr/bin/docker compose run --rm batch python -m homeiot_batch.run_archive
```

`/etc/systemd/system/homeiot-batch.timer`:
```ini
[Unit]
Description=HomeIot batch archive timer

[Timer]
OnCalendar=*-*-* 00:10:00
Persistent=true

[Install]
WantedBy=timers.target
```

有効化:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now homeiot-batch.timer
```

ログ確認:
```bash
sudo journalctl -u homeiot-batch.service -n 100 --no-pager
```

#### Idempotency
- Parquet: 同一日付を再実行すると `dt=YYYY-MM-DD` を削除して再生成
- DuckDB: 挿入前に対象日を DELETE するため重複しない

### Security Notes
- 公開ポートは 8883 のみ（22/SSH は運用に合わせて）
- 1883/3000/8000/8086 は開けない

UFW 例:
```bash
sudo ufw allow 22/tcp
sudo ufw allow 8883/tcp
sudo ufw deny 1883/tcp
sudo ufw deny 3000/tcp
sudo ufw deny 8000/tcp
sudo ufw deny 8086/tcp
sudo ufw enable
```
