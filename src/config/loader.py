from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

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


def _canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def compute_config_hash(raw: dict[str, Any]) -> str:
    payload = dict(raw)
    meta = dict(payload.get("meta", {}))
    meta.pop("config_hash", None)
    payload["meta"] = meta
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def apply_schema_defaults(instance: Any, schema: dict[str, Any]) -> Any:
    if not isinstance(instance, dict):
        return instance
    properties = schema.get("properties", {})
    for key, prop_schema in properties.items():
        if key not in instance and "default" in prop_schema:
            instance[key] = prop_schema["default"]
        if key in instance:
            apply_schema_defaults(instance[key], prop_schema)
    return instance


def load_and_validate_config(config_path: str | Path, schema_path: str | Path, env: dict[str, str] | None = None):
    raw = load_raw_config(config_path)
    schema = load_schema(schema_path)
    apply_schema_defaults(raw, schema)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(raw), key=lambda err: list(err.path))
    if errors:
        rendered = "; ".join(
            f"{'/'.join(str(p) for p in err.path) or '<root>'}: {err.message}" for err in errors
        )
        raise ValidationError(f"schema validation failed: {rendered}")
    try:
        raw["meta"]["config_hash"] = compute_config_hash(raw)
    except Exception as exc:  # noqa: BLE001
        raise ValidationError(f"failed to compute config hash: {exc}") from exc
    semantic_validate(raw, env=env)
    return normalize_config(raw)
