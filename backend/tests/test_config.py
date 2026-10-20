import importlib

import app.config as config_module


def test_settings_in_the_env_file_are_really_used(tmp_path, monkeypatch):
    """Regression: .env used to be loaded after Config read its settings, so it was silently ignored."""
    env_file = tmp_path / "test.env"
    env_file.write_text("ROUTING_PROVIDER=osrm\nOSRM_TIME_FACTOR=1.3\nCORS_ORIGIN=http://example.test\n")
    for name in ("ROUTING_PROVIDER", "OSRM_TIME_FACTOR", "CORS_ORIGIN"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ENV_FILE", str(env_file))
    try:
        reloaded = importlib.reload(config_module)
        assert reloaded.Config.ROUTING_PROVIDER == "osrm"
        assert reloaded.Config.OSRM_TIME_FACTOR == 1.3
        assert reloaded.Config.CORS_ORIGIN == "http://example.test"
        assert reloaded.TestConfig.ROUTING_PROVIDER == "haversine"      # tests stay offline whatever .env says
    finally:
        monkeypatch.undo()
        for name in ("ROUTING_PROVIDER", "OSRM_TIME_FACTOR", "CORS_ORIGIN"):
            monkeypatch.delenv(name, raising=False)
        importlib.reload(config_module)


def test_a_real_environment_variable_beats_the_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / "test.env"
    env_file.write_text("ROUTING_PROVIDER=osrm\n")
    monkeypatch.setenv("ENV_FILE", str(env_file))
    monkeypatch.setenv("ROUTING_PROVIDER", "haversine")           # e.g. set by Docker or CI
    try:
        assert importlib.reload(config_module).Config.ROUTING_PROVIDER == "haversine"
    finally:
        monkeypatch.undo()
        importlib.reload(config_module)
