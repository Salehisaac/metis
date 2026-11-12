import importlib
import sys

import pytest

GOOD = {"DATABASE_URL": "postgresql://app:pw@db:5432/app", "OAUTH_CLIENT_SECRET": "oauth-s3cret"}


def load():
    sys.modules.pop("settings", None)
    return importlib.import_module("settings")


def test_required_values_and_defaults():
    s = load().load_settings(GOOD)
    assert (s.database_url, s.oauth_client_secret) == (GOOD["DATABASE_URL"], "oauth-s3cret")
    assert (s.port, s.debug, s.log_level) == (8000, False, "INFO")


def test_optional_values_are_converted_and_trimmed():
    env = {**GOOD, "PORT": " 8080 ", "DEBUG": " Yes ", "LOG_LEVEL": "debug", "DATABASE_URL": "  sqlite:///x.db\n"}
    s = load().load_settings(env)
    assert (s.port, s.debug, s.log_level, s.database_url) == (8080, True, "DEBUG", "sqlite:///x.db")
    for raw, expected in [("true", True), ("1", True), ("YES", True), ("false", False), ("0", False), ("No", False)]:
        assert load().load_settings({**GOOD, "DEBUG": raw}).debug is expected, raw


def test_missing_required_values_are_all_reported():
    m = load()
    with pytest.raises(m.ConfigError) as err:
        m.load_settings({})
    assert "DATABASE_URL" in str(err.value) and "OAUTH_CLIENT_SECRET" in str(err.value), "name every missing variable at once"


def test_blank_value_counts_as_missing():
    m = load()
    with pytest.raises(m.ConfigError) as err:
        m.load_settings({**GOOD, "OAUTH_CLIENT_SECRET": "   "})
    assert "OAUTH_CLIENT_SECRET" in str(err.value)


def test_invalid_port_is_rejected():
    m = load()
    for bad in ["80a", "", "0", "65536", "-1", "8080.0"]:
        with pytest.raises(m.ConfigError) as err:
            m.load_settings({**GOOD, "PORT": bad})
        assert "PORT" in str(err.value), bad


def test_invalid_flag_or_level_is_rejected():
    m = load()
    for name, bad in [("DEBUG", "maybe"), ("DEBUG", "on"), ("DEBUG", ""), ("LOG_LEVEL", "LOUD")]:
        with pytest.raises(m.ConfigError) as err:
            m.load_settings({**GOOD, name: bad})
        assert name in str(err.value), (name, bad)


def test_secret_stays_out_of_repr_and_errors():
    m = load()
    assert "oauth-s3cret" not in repr(m.load_settings(GOOD))
    with pytest.raises(m.ConfigError) as err:
        m.load_settings({**GOOD, "PORT": "x"})
    assert "oauth-s3cret" not in str(err.value)


def test_only_the_given_mapping_is_read(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "from-process-env")
    monkeypatch.setenv("OAUTH_CLIENT_SECRET", "from-process-env")
    m = load()
    with pytest.raises(m.ConfigError):
        m.load_settings({})
