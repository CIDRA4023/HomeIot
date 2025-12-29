# Batch実行手順（Influx → Parquet → DuckDB）

## 概要
前日（JST）の電力データを InfluxDB から取り出し、`/data/parquet/raw_meter_readings/dt=YYYY-MM-DD/` に Parquet 出力した後、Parquet をソースに DuckDB `/data/duckdb/home_energy.duckdb` の `raw_meter_readings` へロードする。

## 前提
- ルートで `.env.sample` を `.env` にコピーし、必要なら INFLUX_* / DUCKDB_PATH / PARQUET_BASE_DIR を調整
- `docker compose up -d influxdb mqtt` で InfluxDB と Mosquitto を起動済み（mqtt_gateway は任意）
- `docker-compose.yml` で `/data/duckdb` と `/data/parquet` がホストにマウントされる

## サンプルデータ投入（任意）
開発用に対象期間へサンプルを入れる：
```bash
docker compose run --rm batch python -m homeiot_batch.dev_seed
```
主なオプション:
- `--start-utc 2025-12-16T15:00:00Z` 開始時刻(UTC)
- `--interval-minutes 30` ポイント間隔
- `--count 24` 件数
- `--source meter1` sourceタグ（省略時は SOURCE_DEFAULT）

## 日次アーカイブ実行
```bash
docker compose run --rm batch python -m homeiot_batch.run_archive
```
実行内容:
1. 前日(JST)の 00:00〜24:00 を UTC に変換して InfluxDB から取得
2. Parquet を一時ディレクトリに書き出し、`dt=YYYY-MM-DD` へ原子的にリネーム
3. DuckDB は `home_energy.next.duckdb` に書き込み（対象日 DELETE → Parquet から INSERT）
4. `PRAGMA integrity_check` と `CHECKPOINT` 実行後、`home_energy.duckdb` と原子的に入れ替え
   - 既存DBは `home_energy.prev.duckdb` に退避

## 出力確認
- Parquet: `ls data/parquet/raw_meter_readings/dt=YYYY-MM-DD`
- DuckDB 件数例: `duckdb data/duckdb/home_energy.duckdb "SELECT COUNT(*) FROM raw_meter_readings;"` （手元に duckdb コマンドがある場合）

## 定期実行（systemd timer）
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

## 冪等性
- Parquet: 同一日付を再実行すると `dt=YYYY-MM-DD` を削除して再生成
- DuckDB: 挿入前に対象日を DELETE するため重複しない
