### Uptime Kuma Push 監視

MQTT の publish 成功時に Uptime Kuma へ ping して、ラズパイ側の生存確認に使えます。

1) サーバー側で Uptime Kuma を起動します。

```
docker compose up -d uptime_kuma
```

2) `http://<server>:3001` で Uptime Kuma を開き、Push 監視を作成します。
3) 作成された Push URL を `device/raspi-zero2/.env` の `UPTIME_KUMA_PUSH_URL` に設定します。
4) ラズパイのプロセスを起動すると、MQTT publish 成功時に Uptime Kuma に push します。