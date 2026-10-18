"""Five-layer FastAPI configuration with strict precedence and secret masking."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parent

DEFAULTS: dict[str, Any] = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}
TRUE_VALUES = {"true", "1", "yes", "on"}

app = FastAPI(title="Effective Configuration API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)


def canonical_key(key: str) -> str:
    """Normalize APP_ prefixed and non-prefixed config keys."""
    normalized = str(key).strip().lower()
    if normalized.startswith("app_"):
        normalized = normalized[4:]
    return normalized


def read_yaml_layer(environment: str) -> dict[str, Any]:
    """Read an environment-specific YAML config relative to this module."""
    if not environment.replace("-", "").replace("_", "").isalnum():
        raise ValueError("Invalid environment name")
    file = ROOT / f"config.{environment}.yaml"
    if not file.exists():
        return {}
    values = yaml.safe_load(file.read_text(encoding="utf-8")) or {}
    if not isinstance(values, dict):
        raise ValueError(f"{file.name} must contain a YAML mapping")
    return {canonical_key(k): v for k, v in values.items()}


def read_dotenv_layer() -> dict[str, Any]:
    """Read .env without mutating the actual OS environment."""
    entries = dotenv_values(ROOT / ".env")
    result: dict[str, Any] = {}

    # The unprefixed .env alias has the same meaning as APP_WORKERS.
    if entries.get("NUM_WORKERS") is not None:
        result["workers"] = entries["NUM_WORKERS"]

    for key, value in entries.items():
        if value is None or key == "NUM_WORKERS":
            continue
        normalized = canonical_key(key)
        if normalized != "env":
            result[normalized] = value
    return result


def read_os_layer() -> dict[str, str]:
    """Only APP_* process variables belong to this layer."""
    return {
        canonical_key(k): v
        for k, v in os.environ.items()
        if k.upper().startswith("APP_") and k.upper() != "APP_ENV"
    }


def coerce(key: str, value: Any) -> Any:
    if key in ("port", "workers"):
        return int(value)
    if key == "debug":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in TRUE_VALUES
    return str(value)


def effective_config(overrides: list[str]) -> dict[str, Any]:
    environment = os.environ.get("APP_ENV", "development").strip().lower()

    # Each update represents a complete layer, with later layers winning.
    raw: dict[str, Any] = dict(DEFAULTS)
    raw.update(read_yaml_layer(environment))
    raw.update(read_dotenv_layer())
    raw.update(read_os_layer())

    for entry in overrides:
        if "=" not in entry:
            raise HTTPException(status_code=422, detail="Each set parameter must be key=value")
        name, value = entry.split("=", 1)
        name = canonical_key(name)
        if not name:
            raise HTTPException(status_code=422, detail="Override key cannot be empty")
        raw[name] = value

    try:
        result = {key: coerce(key, value) for key, value in raw.items()}
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Invalid integer config value") from exc

    # Mask even if overridden by a new secret in a query parameter.
    result["api_key"] = "****"
    return result


@app.get("/effective-config")
def get_effective_config(set_values: list[str] = Query(default=[], alias="set")) -> dict[str, Any]:
    return effective_config(set_values)
