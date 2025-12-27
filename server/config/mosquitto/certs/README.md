# MQTT TLS 証明書の生成手順（自己署名）

以下は最小構成の例です。`mqtt.example.com` は実際の MQTT 用 FQDN に置き換えてください。

```bash
mkdir -p server/config/mosquitto/certs
cd server/config/mosquitto/certs

# CA 作成
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 \
  -subj "/CN=HomeIoT CA" -out ca.crt

# サーバ証明書
openssl genrsa -out server.key 2048
openssl req -new -key server.key -subj "/CN=mqtt.example.com" -out server.csr
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out server.crt -days 825 -sha256
```

生成物:
- `ca.crt`（ラズパイへ配布）
- `server.crt` / `server.key`（VPS の Mosquitto 用）

注意:
- `ca.key` と `server.key` は厳重に管理し、Git にはコミットしません。
