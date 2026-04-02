from __future__ import annotations

import argparse

from app.bootstrap import bootstrap_engine


def run() -> int:
    parser = argparse.ArgumentParser(description="Safety-first spot grid engine")
    parser.add_argument("--config", required=True)
    parser.add_argument("--schema", default="config/strategy.schema.json")
    args = parser.parse_args()

    engine = bootstrap_engine(args.config, args.schema)
    engine.bootstrap()
    return 0
