# Grafana (Influx + DuckDB)

## 使い方
1. DuckDB と Parquet がマウントされる状態で `docker compose up -d grafana` を実行
2. 初期ユーザー/パスワードは `GF_SECURITY_ADMIN_USER` / `GF_SECURITY_ADMIN_PASSWORD` （デフォルト: admin/admin）
3. `http://localhost:3000` で Grafana にログインし、ダッシュボード `Home Energy - Realtime` / `Home Energy - Daily` を確認

## プラグイン（DuckDB datasource）
- 署名なしプラグイン `motherduck-duckdb-datasource` を `server/grafana/plugins/motherduck-duckdb-datasource/` に配置してください
- 公式手順: https://github.com/motherduckdb/grafana-duckdb-datasource
- Grafana イメージは Ubuntu 系 (`grafana/grafana:latest-ubuntu`) を使用し、環境変数 `GF_PLUGINS_ALLOW_LOADING_UNSIGNED_PLUGINS=motherduck-duckdb-datasource` を有効化済み

## プロビジョニング
- データソース: `server/grafana/provisioning/datasources/datasources.yml`
  - InfluxDB (Flux, token利用), DuckDB (ローカルファイル参照)
- ダッシュボード: `server/grafana/provisioning/dashboards/dashboards.yml`
  - `server/grafana/dashboards/` 配下の JSON を自動読み込み

## 追加の設定
- ポートは `GRAFANA_PORT`（デフォルト 3000）で変更可
- 時刻は `TZ` で指定（デフォルト `Asia/Tokyo`）
