from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import validate

from config.semantic_validation import semantic_validate
from config.normalizer import normalize_config
from domain.errors import ConfigError, ValidationError


def load_schema(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text())


def load_raw_config(path: str | Path) -> dict[str, Any]:
    try:
        return json.loads(Path(path).read_text())
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid JSON: {exc}") from exc


def load_and_validate_config(config_path: str | Path, schema_path: str | Path, env: dict[str, str] | None = None):
    raw = load_raw_config(config_path)
    schema = load_schema(schema_path)
    try:
        validate(instance=raw, schema=schema)
    except Exception as exc:  # noqa: BLE001
        raise ValidationError(f"schema validation failed: {exc}") from exc
    semantic_validate(raw, env=env)
    return normalize_config(raw)
