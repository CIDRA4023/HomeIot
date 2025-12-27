# VPS セットアップ手順（MQTT TLS + Cloudflare Tunnel）

## 前提
- Cloudflare アカウントとドメインが準備済み
- Cloudflare Tunnel を作成済み（トークン方式）
- DNS で `grafana.example.com` / `app.example.com` を Tunnel に向ける
- MQTT の接続先ホスト名/ IP を決めておく（証明書の SAN と一致が必須）

## .env の設定
`server/.env.sample` をルート直下の `.env` にコピーして編集します。

```bash
cp server/.env.sample .env
```

設定例:
```
CLOUDFLARE_TUNNEL_TOKEN=your-token
MQTT_USER=homeiot
MQTT_PASSWORD=change-me
MQTT_HOST=mqtt.example.com
MQTT_BROKER_URL=mqtts://homeiot:change-me@mqtt.example.com:8883
MQTT_TLS_CA_CERT=/etc/ssl/certs/homeiot-ca.crt
MQTT_TOPIC=home/power
```

補足:
- `MQTT_BROKER_URL` はサーバー内の mqtt_gateway 用（TLS 接続）
- `server/config/mosquitto/certs/ca.crt` を `app` へマウントする（`/etc/ssl/certs/homeiot-ca.crt`）
- 外部公開は 8883 のみ（TLS 必須）
- ホスト名/IP は証明書の SAN と一致させる（IP 直指定する場合は SAN に IP を入れる）

## Cloudflare Tunnel の設定（トークン方式）
トークン方式では Cloudflare 側の設定が優先されます。以下を Cloudflare Zero Trust で設定します。

- Tunnels → 対象トンネル → Public Hostnames
  - `grafana.example.com` → `http://grafana:3000`
  - `app.example.com` → `http://app:8000`


## MQTT TLS 証明書の作成
`server/config/mosquitto/certs/README.md` の手順で `ca.crt` / `server.crt` / `server.key` を作成します。
SAN 付き証明書が必須です（DNS 名で接続する例 / IP で接続する例）。

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

## Mosquitto 認証情報の作成
`passwords` はコミットしないため、生成が必要です。

```bash
docker run --rm -v "$PWD/server/config/mosquitto:/mosquitto/config" \
  eclipse-mosquitto:2.0 mosquitto_passwd -c /mosquitto/config/passwords "${MQTT_USER}"
```

ACL は `server/config/mosquitto/aclfile` を編集して調整してください。

## 起動
```bash
docker compose up -d
docker compose logs -f cloudflared
```
`.env` を変更した場合は、`app` を再作成して反映します。
```bash
docker compose up -d --force-recreate app
```

運用時は `cloudflared` のイメージを固定タグにすることを推奨します。

## ラズパイ側 MQTT 設定例
`ca.crt` をラズパイへ配布し、`/etc/ssl/certs/homeiot-ca.crt` に配置してから設定します。

例:
```bash
scp server/config/mosquitto/certs/ca.crt pi@raspi:/etc/ssl/certs/homeiot-ca.crt
```

```
MQTT_BROKER_URL=mqtts://homeiot:change-me@mqtt.example.com:8883
MQTT_TLS_CA_CERT=/etc/ssl/certs/homeiot-ca.crt
MQTT_TOPIC=home/power
```
IP 直指定で接続する場合は、上記のホスト名を IP に置き換え、証明書の SAN も IP に合わせます。

## セキュリティ注意
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
