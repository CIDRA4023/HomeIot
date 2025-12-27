# VPS セットアップ手順（MQTT TLS + Cloudflare Tunnel）

## 前提
- Cloudflare アカウントとドメインが準備済み
- Cloudflare Tunnel を作成済み（トークン方式）
- DNS で `grafana.example.com` / `app.example.com` を Tunnel に向ける

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
MQTT_BROKER_URL=mqtt://homeiot:change-me@mqtt:1883
MQTT_TOPIC=home/power
```

補足:
- `MQTT_BROKER_URL` はサーバー内の mqtt_gateway 用（TLS なし、内部接続）
- 外部公開は 8883 のみ（TLS 必須）

## Cloudflare Tunnel の設定
`server/cloudflare/config.yml` のホスト名を実際の FQDN に変更してください。

```yaml
ingress:
  - hostname: grafana.example.com
    service: http://grafana:3000
  - hostname: app.example.com
    service: http://app:8000
  - service: http_status:404
```

## MQTT TLS 証明書の作成
`server/config/mosquitto/certs/README.md` の手順で `ca.crt` / `server.crt` / `server.key` を作成します。

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

運用時は `cloudflared` のイメージを固定タグにすることを推奨します。

## ラズパイ側 MQTT 設定例
`ca.crt` をラズパイへ配布し、以下のように設定します。

```
MQTT_BROKER_URL=mqtts://homeiot:change-me@mqtt.example.com:8883
MQTT_TLS_CA_CERT=/etc/ssl/certs/homeiot-ca.crt
MQTT_TOPIC=home/power
```

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
