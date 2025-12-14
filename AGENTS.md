# Repository Guidelines

## プロジェクト構成
- uv を使った Python モノレポ (root `pyproject.toml` / `ty.toml` / `pytest.ini`)。開発時は Python 3.12+（デバイス側は 3.13 以上推奨）。
- `device/raspi-zero2/`: Raspberry Pi Zero2 向けクライアント。エントリは `src/homeiot_device_raspi/main.py`、環境例は `.env.sample`。
- `server/mqtt_gateway/`: FastAPI 製の MQTT→Influx ブリッジ。`Dockerfile` と `src/homeiot_mqtt_gateway/main.py` を中心に構成。
- `server/config/mosquitto/`: MQTT ブローカー設定。`docker-compose.yml` で app / InfluxDB / Mosquitto をまとめて起動。

## セットアップと主要コマンド
- 依存インストール: `uv sync --all-groups`（ルートで実行すると dev 依存も含め全ワークスペースを同期）。
- デバイス実行例: `cd device/raspi-zero2 && cp .env.sample .env && uv sync && uv run python -m homeiot_device_raspi.main`
- サーバー開発実行: `cd server/mqtt_gateway && uv sync && uv run uvicorn homeiot_mqtt_gateway.main:app --reload --host 0.0.0.0 --port 8000`
- コンテナ起動: ルートで `.env.sample` を `.env` にコピー後、`docker compose up -d`。ログ確認は `docker compose logs -f app`。
- Lint/Format: `uv run ruff check .`（必要に応じて `ruff format .`）。型ガードは `uv run ty --config ty.toml` を利用。

## コーディングスタイルと命名
- Python は 4 スペースインデント、型ヒント必須。関数/変数は `snake_case`、クラスは `PascalCase`、定数・環境変数は `UPPER_SNAKE_CASE`。
- モジュール名はパッケージに揃える（例: `homeiot_mqtt_gateway`, `homeiot_device_raspi`）。環境変数は `.env.sample` を基に追加・命名する。
- Lint 警告は可能な限り解消し、例外がある場合は理由をコメントに簡潔に記載。

## テスト
- テストフレームワークは `pytest`。新規テストは各プロジェクト直下に `tests/test_*.py` で配置（例: `server/mqtt_gateway/tests/test_main.py`）。
- 実行: ルートで `uv run pytest`（全体）、サブプロジェクトのみなら `uv run pytest device/raspi-zero2` などで対象を絞る。
- 外部サービス（MQTT/Influx）依存のテストは docker-compose を用いた統合テストを推奨し、接続先を `.env` で明示する。

## コミットと Pull Request

### コミットメッセージ
- 1行目は短い動詞始まりで、何をしたかが分かること。
- 原則として Conventional Commits 互換のプレフィックスを使用する
  （`feat:`, `fix:`, `chore:`, `docs:`, `test:` など）。
- subject 行は 72 文字以内を目安に簡潔に書く。
- 1 コミット 1 目的を原則とするsし、設定や環境変数の変更は
  メッセージ本文にも必ず明記する。

### Pull Request
- PR には以下を含めること：
  - 目的 / 背景
  - 主な変更点
  - 動作確認コマンドとその結果
  - API や設定変更の有無と影響範囲
  - 関連 Issue（あれば）
- 挙動が分かるログやスクリーンショットがあれば添付する。
- レビュー観点を事前に箇条書きすると、レビューがスムーズになる。