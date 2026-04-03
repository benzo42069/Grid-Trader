from __future__ import annotations

import os
from decimal import Decimal

from config.loader import load_and_validate_config
from domain.enums import RuntimeMode
from domain.errors import ValidationError
from domain.models import BalanceSnapshot, InventorySnapshot, PnLSnapshot
from exchange.adapters.kraken_spot import KrakenSpotAdapter
from exchange.adapters.mock_spot import MockSpotAdapter
from ledger.balances import BalanceLedger
from ledger.inventory import InventoryLedger
from ledger.pnl import PnLLedger
from persistence.sqlite_store import SQLiteStore
from strategy.grid_engine import GridEngine
from telemetry.logging import configure_logging
from telemetry.metrics import NullMetrics


def _build_adapter(cfg):
    name = cfg.exchange.name.lower()
    if name == "mock_spot":
        return MockSpotAdapter()
    if name == "kraken":
        api_key = os.getenv("KRAKEN_API_KEY", "")
        api_secret = os.getenv("KRAKEN_API_SECRET", "")
        if cfg.runtime.mode == RuntimeMode.LIVE and (not api_key or not api_secret):
            raise ValidationError("KRAKEN_API_KEY and KRAKEN_API_SECRET must be set for live Kraken trading")
        return KrakenSpotAdapter(api_key=api_key, api_secret=api_secret)
    raise ValidationError(f"unsupported exchange adapter: {cfg.exchange.name}")


def bootstrap_engine(config_path: str, schema_path: str, env: dict[str, str] | None = None) -> GridEngine:
    cfg = load_and_validate_config(config_path, schema_path, env=env)
    configure_logging(cfg.telemetry.log_level)
    adapter = _build_adapter(cfg)
    store = SQLiteStore(cfg.persistence.sqlite_path)
    if cfg.runtime.mode == RuntimeMode.PAPER:
        start_bal = BalanceSnapshot(
            free_quote=Decimal("100000"),
            locked_quote=Decimal("0"),
            free_base=Decimal("10000"),
            locked_base=Decimal("0"),
        )
    else:
        start_bal = adapter.fetch_balances(cfg.market.symbol)
    ledgers = {
        "balances": BalanceLedger(BalanceSnapshot(start_bal.free_quote, start_bal.locked_quote, start_bal.free_base, start_bal.locked_base)),
        "inventory": InventoryLedger(InventorySnapshot(Decimal("0"), Decimal("0"))),
        "pnl": PnLLedger(PnLSnapshot(Decimal("0"), Decimal("0"))),
    }
    return GridEngine(cfg, adapter, store, ledgers, NullMetrics())
