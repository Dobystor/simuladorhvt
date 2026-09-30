"""YAML configuration loading and ServerProfile validation.

Loads all Server_Profiles from a YAML configuration file at startup. Validation
is strict and fail-fast: any problem (missing file, bad YAML, zero profiles,
duplicate names, missing required fields) causes the process to print the file
path and reason to stderr and exit with a non-zero code before any FastAPI app
is created.

Requirements: 1.1, 1.2, 17.4, 17.7
"""

from __future__ import annotations

import os
import sys

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

DEFAULT_CONFIG_PATH = "config.yaml"
CONFIG_PATH_ENV_VAR = "SIMULATOR_CONFIG"


class RabbitMQConfig(BaseModel):
    host: str
    port: int = 5672
    username: str
    password: str
    vhost: str = "/"

    @field_validator("host", "username", "password")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("must be a non-empty string")
        return value


class RethinkDBConfig(BaseModel):
    host: str
    port: int = 28015

    @field_validator("host")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("must be a non-empty string")
        return value


class RedisConfig(BaseModel):
    """Optional; not currently used by the simulator."""

    host: str
    port: int = 6379


class OAuthClient(BaseModel):
    """An IdentityServer client candidate for the password grant."""

    client_id: str
    client_secret: str


class ServerProfile(BaseModel):
    name: str
    api_base_url: str
    rabbitmq: RabbitMQConfig
    rethinkdb: RethinkDBConfig
    redis: RedisConfig | None = None
    # OAuth token endpoint path (relative to api_base_url) and scope.
    token_path: str = "/api/openid/connect/token"
    oauth_scope: str = "smartflow IdentityServerApi offline_access"
    # Client credentials tried in order (first that works wins). Defaults match
    # the SmartFlow clients used by the reference haulage bot.
    oauth_clients: list[OAuthClient] = Field(
        default_factory=lambda: [
            OAuthClient(
                client_id="private.networking.app",
                client_secret="UxwYJsELeTnSc2Zz642K",
            ),
            OAuthClient(client_id="smartflow.csharp.client", client_secret="secret"),
        ]
    )

    @field_validator("name", "api_base_url")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("must be a non-empty string")
        return value

    @property
    def sanitized_name(self) -> str:
        """A queue-name-safe version of the profile name."""
        return "".join(c if c.isalnum() else "_" for c in self.name)


class SimulatorConfig(BaseModel):
    server_profiles: list[ServerProfile] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_profiles(self) -> "SimulatorConfig":
        if not self.server_profiles:
            raise ValueError("server_profiles must contain at least one entry")
        names = [p.name for p in self.server_profiles]
        duplicates = {n for n in names if names.count(n) > 1}
        if duplicates:
            raise ValueError(
                f"profile names must be unique; duplicates: {sorted(duplicates)}"
            )
        return self

    def get_profile(self, name: str) -> ServerProfile | None:
        for profile in self.server_profiles:
            if profile.name == name:
                return profile
        return None


class ConfigError(Exception):
    """Raised when the configuration cannot be loaded or is invalid."""


def _resolve_config_path(config_path: str | None) -> str:
    if config_path is not None:
        return config_path
    return os.environ.get(CONFIG_PATH_ENV_VAR, DEFAULT_CONFIG_PATH)


def load_config(config_path: str | None = None) -> SimulatorConfig:
    """Load and validate the simulator configuration.

    Raises ConfigError with a descriptive message (including the file path) on
    any failure. Callers at startup should catch this and exit the process.
    """
    path = _resolve_config_path(config_path)

    if not os.path.isfile(path):
        raise ConfigError(f"Configuration file not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise ConfigError(f"Configuration file {path} contains invalid YAML: {exc}")
    except OSError as exc:
        raise ConfigError(f"Configuration file {path} could not be read: {exc}")

    if raw is None:
        raise ConfigError(f"Configuration file {path} is empty")

    if not isinstance(raw, dict):
        raise ConfigError(
            f"Configuration file {path} must contain a top-level mapping"
        )

    try:
        return SimulatorConfig(**raw)
    except ValidationError as exc:
        raise ConfigError(f"Configuration file {path} is invalid: {exc}")


def load_config_or_exit(config_path: str | None = None) -> SimulatorConfig:
    """Load config; on failure, print to stderr and exit with code 1.

    Used at process startup so no FastAPI app is created on invalid config.
    """
    try:
        return load_config(config_path)
    except ConfigError as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        sys.exit(1)
