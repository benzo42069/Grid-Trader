from __future__ import annotations

import argparse
import logging
import time

from dotenv import load_dotenv

from app.bootstrap import bootstrap_engine
from domain.enums import RuntimeMode
from domain.errors import ValidationError

LOGGER = logging.getLogger(__name__)


def run() -> int:
    parser = argparse.ArgumentParser(prog="crypt_ex", description="CryptEX Kraken-ready grid trading CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run one strategy")
    run_parser.add_argument("--strategy", required=True, help="Path to strategy JSON")
    run_parser.add_argument("--schema", default="config/strategy.schema.json", help="Path to schema")
    run_parser.add_argument("--live", action="store_true", help="Required confirmation for live trading")
    run_parser.add_argument("--env-file", default=".env", help="Optional .env file path")
    run_parser.add_argument("--loop-interval", type=float, default=1.0, help="Main loop interval in seconds")

    args = parser.parse_args()
    if args.command != "run":
        raise ValidationError("unsupported command")

    load_dotenv(args.env_file)
    engine = bootstrap_engine(args.strategy, args.schema)

    if engine.cfg.runtime.mode == RuntimeMode.LIVE and not args.live:
        raise ValidationError("live mode requested by strategy. Re-run with --live to confirm real trading")

    LOGGER.info(
        "startup summary: exchange=%s symbol=%s mode=%s allocation=%s",
        engine.cfg.exchange.name,
        engine.cfg.market.symbol,
        engine.cfg.runtime.mode.value,
        engine.cfg.strategy.total_quote_allocation,
    )
    engine.bootstrap()
    engine.run_forever(loop_interval_seconds=args.loop_interval)
    return 0
