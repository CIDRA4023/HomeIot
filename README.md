# Home IoT

Raspberry Pi と VPS の両方を 1 リポジトリで管理するための最小構成です。

```
home-iot/
  README.md
  device/
    main.py            # ラズパイ用のエントリポイント
    pyproject.toml     # uv や pip で使う依存定義
    .env.sample        # momonga / InfluxDB の設定例
  server/
    docker-compose.yml # VPS 上で起動するスタック
    app/
      Dockerfile
      app.py           # API（FastAPI）サンプル
    .env.sample        # InfluxDB / MQTT などの設定例
```

## Device (Raspberry Pi)

```
cd device
cp .env.sample .env          # Bルートや InfluxDB の接続設定を書き換える
uv sync                      # もしくは: pip install -r <generated requirements>
uv run python main.py        # もしくは: python main.py
```

### 主な環境変数

- `RBID`, `B_ROUTE_PWD`, `DEVICE`: momonga でスマートメーターへ接続するための B ルート情報
- `INFLUX_URL`, `INFLUX_TOKEN`, `INFLUX_ORG`, `INFLUX_BUCKET`: 書き込み先の InfluxDB 設定

## Server (VPS)

```
cd server
cp .env.sample .env           # パスワードやポートを上書き
docker compose up -d
```

- `app/` は独自の API コンテナを置く場所です（FastAPI の最小実装を同梱）。
- `docker-compose.yml` はアプリと一緒に InfluxDB・MQTT ブローカーを公式イメージで起動します。

任意の VPS 上で `docker compose logs -f` でログを確認しつつ、必要になったら DB バックアップ先やボリューム名を調整してください。
