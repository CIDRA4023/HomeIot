import homeiot_device_raspi.main as main


class DummyClient:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.username = None
        self.password = None
        self.connect_args = None
        self.loop_started = False
        self.reconnect_delays = None
        self.on_connect = None
        self.on_disconnect = None

    def username_pw_set(self, username, password=None):
        self.username = username
        self.password = password

    def reconnect_delay_set(self, min_delay, max_delay):
        self.reconnect_delays = (min_delay, max_delay)

    def connect_async(self, host, port):
        self.connect_args = (host, port)

    def loop_start(self):
        self.loop_started = True


def test_validate_required_env_missing(monkeypatch):
    monkeypatch.setattr(main, "rbid", None)
    monkeypatch.setattr(main, "pwd", "pwd")
    monkeypatch.setattr(main, "dev", "dev")

    try:
        main.validate_required_env()
    except SystemExit:
        return
    raise AssertionError("Expected SystemExit when required env is missing")


def test_validate_required_env_ok(monkeypatch):
    monkeypatch.setattr(main, "rbid", "rbid")
    monkeypatch.setattr(main, "pwd", "pwd")
    monkeypatch.setattr(main, "dev", "/dev/ttyUSB0")

    main.validate_required_env()


def test_build_mqtt_client_missing_url(monkeypatch):
    monkeypatch.setattr(main, "MQTT_BROKER_URL", None)

    assert main.build_mqtt_client() is None


def test_build_mqtt_client_invalid_url(monkeypatch):
    monkeypatch.setattr(main, "MQTT_BROKER_URL", "mqtt://")

    assert main.build_mqtt_client() is None


def test_build_mqtt_client_valid_url(monkeypatch):
    monkeypatch.setattr(main.mqtt, "Client", DummyClient)
    monkeypatch.setattr(main, "MQTT_BROKER_URL", "mqtt://user:pass@localhost:1884")

    client = main.build_mqtt_client()

    assert isinstance(client, DummyClient)
    assert client.username == "user"
    assert client.password == "pass"
    assert client.connect_args == ("localhost", 1884)
    assert client.loop_started is True
    assert client.reconnect_delays == (1, 60)
    assert client.on_connect is not None
    assert client.on_disconnect is not None
