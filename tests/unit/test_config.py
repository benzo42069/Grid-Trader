from pathlib import Path

import pytest

from config.loader import load_and_validate_config
from domain.enums import RuntimeMode
from domain.errors import ValidationError


def test_schema_and_semantic_pass():
    cfg = load_and_validate_config("config/examples/paper_spot_grid.json", "config/strategy.schema.json", env={})
    assert cfg.runtime.mode == RuntimeMode.PAPER


def test_semantic_live_requires_env(tmp_path: Path):
    raw = Path("config/examples/live_spot_grid.json").read_text()
    fp = tmp_path / "live.json"
    fp.write_text(raw)
    with pytest.raises(ValidationError):
        load_and_validate_config(fp, "config/strategy.schema.json", env={})
