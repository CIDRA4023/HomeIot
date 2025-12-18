# InfluxDB → Parquet → DuckDB（raw）→ dbt の実装タスク（Codex依頼用）

このMDは **Codex に実装してもらうための依頼書** です。
目的は「VPS上で日次バッチが動き、InfluxDBの前日分データを **Parquet に日次パーティション保存し、そこから DuckDB へ冪等ロード** し、dbtで集計テーブルを作る」ことです。

---

## 0. 前提（リポジトリ構成）

モノレポは以下の形に移行済み（または移行中）とします：

```text
HomeIot/
├─ pyproject.toml                  # uv workspace + dev tools
├─ uv.lock
├─ docker-compose.yml
├─ server/
│  ├─ batch/
│  │  ├─ Dockerfile
│  │  ├─ pyproject.toml
│  │  └─ src/homeiot_batch/...
│  ├─ mqtt_gateway/...
│  └─ dbt/...
├─ data/duckdb/home_energy.duckdb      # volume mount
└─ data/parquet/raw_meter_readings/... # volume mount
```

- Python: 3.12+
- 依存管理: uv
- 追加ツール（ルート側で導入済み想定）: ruff / ty / pytest / pre-commit / import-linter
- InfluxDB: `home_energy` DB、measurement `power` を想定
- MQTT Gateway が InfluxDB に以下 fields を書き込んでいる想定：
  - `instant_power_w`
  - `energy_import_kwh`
  - `energy_export_kwh`（任意）
  - tag: `source`（例: meter1）
- 時刻は Influx の `time`（UTC）を利用し、DuckDB側で JST も保持する

---

## 1. 目標（Doneの定義）

### 1-1. バッチが動く
- VPS上で `docker compose run --rm batch python -m homeiot_batch.run_archive` が成功する
- InfluxDBから「前日 00:00〜24:00（JST）」のデータを取得し、**Parquet (dt=YYYY-MM-DD) に出力した上で DuckDB にロード**する

### 1-2. 冪等
- 同じ日付のバッチを複数回走らせても Parquet と DuckDB が重複しない
  - Parquet: 対象 `dt=YYYY-MM-DD` ディレクトリを削除→一時dirに書き出し→rename で確定
  - DuckDB: 対象日 `DATE(ts_jst)` を DELETE してから Parquet から INSERT

### 1-3. dbtで集計モデルが作れる
- `stg_meter_readings` と `fct_daily_energy` の2つが最低限 `dbt run` で生成できる

### 1-4. テストと静的チェック
- pytest で最低限のユニットテストが通る（変換・日付境界・冪等性）
- ruff / ty が通る

---

## 2. 実装タスク（優先順）

### 2-1. `server/batch` を実装

#### A) 依存・エントリポイント
1. `server/batch/pyproject.toml` を整備（最小依存）
   - 必須: `duckdb`, `influxdb`, `pyarrow`
2. `server/batch/src/homeiot_batch/__init__.py` を作成
3. `server/batch/src/homeiot_batch/run_archive.py` を `python -m homeiot_batch.run_archive` で実行できるようにする

#### B) モジュール分割（推奨）
以下のファイルを作成し、`run_archive.py` はそれらを呼び出す構造にする：

- `config.py`
- `influx_reader.py`
- `transform.py`
- `parquet_writer.py`
- `duckdb_writer.py`
- `logging_conf.py`（任意）

---

### 2-2. 設定（環境変数）
batch コンテナは環境変数で動くようにする（compose側から渡す）：

- `INFLUX_URL` (default: http://influxdb:8086)
- `INFLUX_BUCKET` (default: home_energy)
- `INFLUX_TOKEN`（InfluxDB 2 の Token 認証を使う場合）
- `INFLUX_USERNAME` / `INFLUX_PASSWORD`（Basic認証を使うなら）
- `INFLUX_MEASUREMENT` (default: power)
- `DUCKDB_PATH` (default: /data/duckdb/home_energy.duckdb)
- `PARQUET_BASE_DIR` (default: /data/parquet)
- `PARQUET_COMPRESSION` (default: zstd)
- `PARQUET_ROW_GROUP_SIZE`（任意）
- `TZ` (default: Asia/Tokyo)
- `SOURCE_DEFAULT` (default: meter1)

---

### 2-3. Influx 抽出仕様

#### 対象期間（重要）
- バッチ実行時刻が JST の 0:05〜0:30 を想定
- 抽出期間は **前日 00:00:00 JST 〜 翌日 00:00:00 JST（半開区間）** を推奨
- InfluxへのクエリはUTCに変換して投げる

#### クエリ（InfluxQL例）
- measurement: `power`
- fields: `instant_power_w`, `energy_import_kwh`, `energy_export_kwh`
- tag: `source`

例（擬似）：
```sql
SELECT instant_power_w, energy_import_kwh, energy_export_kwh
FROM power
WHERE time >= '{start_utc_iso}'
  AND time <  '{end_utc_iso}'
```

---

### 2-4. Parquet データセット
- base: `${PARQUET_BASE_DIR}/raw_meter_readings/`
- パーティション: `dt=YYYY-MM-DD`（JST日付の hive-style）
- 列（順序固定・DuckDB と同じ）:
  - `ts_utc`, `ts_jst`, `source`, `instant_power_w`, `energy_import_kwh`, `energy_export_kwh`, `ingested_at`
- 型: timestamp (tz付き), double, string。欠損は 0.0 扱い。
- 書き出し手順: 既存パーティション削除 → `__tmp__` へ書き出し → rename で確定

### 2-5. DuckDB スキーマ（raw）

テーブル名: `raw_meter_readings`

DDL（目安）：

```sql
CREATE TABLE IF NOT EXISTS raw_meter_readings (
  ts_utc TIMESTAMP,
  ts_jst TIMESTAMP,
  source VARCHAR,
  instant_power_w DOUBLE,
  energy_import_kwh DOUBLE,
  energy_export_kwh DOUBLE,
  ingested_at TIMESTAMP
);
```

### 2-6. ロードと冪等戦略
- Parquet から `read_parquet` で INSERT
- INSERT 前に `DELETE FROM raw_meter_readings WHERE DATE(ts_jst) = ?`
- Parquet 側は前述の「削除→tmp書き出し→rename」で常に上書き

---

### 2-7. 変換仕様（transform）

Influxの `points`（dict）を下記の row タプルへ変換：

`(ts_utc, ts_jst, source, instant_power_w, energy_import_kwh, energy_export_kwh, ingested_at)`

- `ts_utc`: Influx `time`（Z）を `datetime` に変換
- `ts_jst`: `ts_utc` を JSTへ変換
- `source`: tagが取れない場合は `SOURCE_DEFAULT`
- 欠損値は `0.0` にする（例：energy_exportが無い時）
- `ingested_at`: now(UTC)

---

----

## 3. dbt 側タスク（最小）

### 3-1. dbtプロジェクトの配置
`server/dbt/` に dbt プロジェクトがある想定。なければ作る。

### 3-2. DuckDBへの接続
- DuckDBファイルは `data/duckdb/home_energy.duckdb`
- `profiles.yml` は example を置いて、実運用ではホストからマウント or 環境変数で差し替え

### 3-3. モデル（最低2つ）
1. `models/staging/stg_meter_readings.sql`
   - `raw_meter_readings` を整形して `date_jst` を付与
2. `models/marts/fct_daily_energy.sql`
   - 日別の使用量とピークを計算
   - `daily_energy_kwh = max(energy_import_kwh) - min(energy_import_kwh)`
   - `peak_w = max(instant_power_w)`

---

## 4. docker-compose 側の追加・更新

### 4-1. batch サービス
`docker-compose.yml` に batch を追加（build: ./server/batch）

- `/data/duckdb` を `./data/duckdb` にマウント
- `/data/parquet` を `./data/parquet` にマウント
- `TZ=Asia/Tokyo` を付与
- Influx / DuckDB / Parquet の env を付与

### 4-2. cron（運用）
cron で以下を実行できる状態にする：

```bash
docker compose run --rm batch python -m homeiot_batch.run_archive
```

cronファイル自体は `server/config/cron/crontab.example` に例として置く（任意）

---

## 5. テスト要件（pytest）

最低限、以下を満たすテストを追加：

1. `transform` が欠損値を 0.0 にする
2. `target_date` の計算が JST で「前日」を正しく指す
3. `duckdb_writer` の DELETE → INSERT が期待通り動く（DuckDBを一時ファイルで）

※ InfluxDB接続を伴うテストはユニットテストでは避け、必要なら `INTEGRATION_TESTS=1` のときのみ動かすなどで分離。

---

## 6. 静的チェック（ruff / ty）

- ruff: `uv run ruff check .` が通る
- ty: `uv run ty` が通る（最低でも batch 配下）

---

## 7. 追加の推奨（あれば）

- `logging` を統一（JSONログ or key=value）
- 例外時に exit code を非0にする
- 取得件数・挿入件数をログに出す（運用で便利）

---

## 8. 納品物（Codexが作るべきファイル一覧）

batch:
- `server/batch/pyproject.toml`
- `server/batch/Dockerfile`
- `server/batch/src/homeiot_batch/run_archive.py`
- `server/batch/src/homeiot_batch/config.py`
- `server/batch/src/homeiot_batch/influx_reader.py`
- `server/batch/src/homeiot_batch/transform.py`
- `server/batch/src/homeiot_batch/duckdb_writer.py`
- `server/batch/tests/test_transform.py`
- `server/batch/tests/test_duckdb_writer.py`

dbt:
- `server/dbt/models/staging/stg_meter_readings.sql`
- `server/dbt/models/marts/fct_daily_energy.sql`
- `server/dbt/profiles.yml.example`（無ければ）

compose:
- ルート `docker-compose.yml` の batch 追加（差分でOK）

---

## 9. 実行確認コマンド（ローカル / VPS）

```bash
# 依存同期
uv sync --group dev

# lint / type / test
uv run ruff check .
uv run ty
uv run pytest

# コンテナ起動（influx/mosquitto/gateway）
docker compose up -d

# batch 手動実行
docker compose run --rm batch python -m homeiot_batch.run_archive

# dbt（任意）
cd server/dbt
dbt run
```

---

以上。ここまでを **小さな差分コミット** で積み上げる形で実装してください。
