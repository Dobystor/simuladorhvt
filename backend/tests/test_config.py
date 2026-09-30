"""Unit tests for configuration loading and validation.

Requirements: 1.2, 17.7
"""

import textwrap

import pytest

from app.config import ConfigError, ServerProfile, load_config

VALID_CONFIG = textwrap.dedent(
    """
    server_profiles:
      - name: "Production"
        api_base_url: "https://prod.example.com"
        rabbitmq:
          host: "prod-rabbit"
          username: "smartflow"
          password: "secret"
        rethinkdb:
          host: "prod-rethink"
      - name: "Staging"
        api_base_url: "https://staging.example.com"
        rabbitmq:
          host: "staging-rabbit"
          username: "smartflow"
          password: "secret"
        rethinkdb:
          host: "staging-rethink"
    """
)


def _write(tmp_path, content):
    path = tmp_path / "config.yaml"
    path.write_text(content, encoding="utf-8")
    return str(path)


def test_valid_config_loads(tmp_path):
    config = load_config(_write(tmp_path, VALID_CONFIG))
    assert len(config.server_profiles) == 2
    assert config.get_profile("Production") is not None
    assert config.get_profile("Staging").rabbitmq.port == 5672  # default applied


def test_missing_file_raises(tmp_path):
    with pytest.raises(ConfigError) as exc:
        load_config(str(tmp_path / "does-not-exist.yaml"))
    assert "not found" in str(exc.value)


def test_malformed_yaml_raises(tmp_path):
    with pytest.raises(ConfigError) as exc:
        load_config(_write(tmp_path, "server_profiles: [unclosed"))
    assert "invalid YAML" in str(exc.value)


def test_empty_file_raises(tmp_path):
    with pytest.raises(ConfigError) as exc:
        load_config(_write(tmp_path, ""))
    assert "empty" in str(exc.value)


def test_zero_profiles_raises(tmp_path):
    with pytest.raises(ConfigError) as exc:
        load_config(_write(tmp_path, "server_profiles: []"))
    assert "at least one" in str(exc.value)


def test_duplicate_profile_names_raises(tmp_path):
    dup = VALID_CONFIG.replace('"Staging"', '"Production"')
    with pytest.raises(ConfigError) as exc:
        load_config(_write(tmp_path, dup))
    assert "unique" in str(exc.value)


def test_missing_required_field_raises(tmp_path):
    missing = textwrap.dedent(
        """
        server_profiles:
          - name: "Production"
            api_base_url: "https://prod.example.com"
            rabbitmq:
              host: "prod-rabbit"
              username: "smartflow"
            rethinkdb:
              host: "prod-rethink"
        """
    )
    with pytest.raises(ConfigError) as exc:
        load_config(_write(tmp_path, missing))
    assert "invalid" in str(exc.value)


def test_sanitized_name_is_queue_safe():
    profile = ServerProfile(
        name="Prod / EU-1",
        api_base_url="https://x",
        rabbitmq={"host": "h", "username": "u", "password": "p"},
        rethinkdb={"host": "h"},
    )
    assert profile.sanitized_name == "Prod___EU_1"
