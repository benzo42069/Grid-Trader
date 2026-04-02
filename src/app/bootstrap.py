from __future__ import annotations

from decimal import Decimal

from config.loader import load_and_validate_config
from domain.models import BalanceSnapshot, InventorySnapshot, PnLSnapshot
from exchange.adapters.mock_spot import MockSpotAdapter
from ledger.balances import BalanceLedger
from ledger.inventory import InventoryLedger
from ledger.pnl import PnLLedger
from persistence.sqlite_store import SQLiteStore
from strategy.grid_engine import GridEngine
from telemetry.logging import configure_logging
from telemetry.metrics import NullMetrics


def bootstrap_engine(config_path: str, schema_path: str, env: dict[str, str] | None = None) -> GridEngine:
    cfg = load_and_validate_config(config_path, schema_path, env=env)
    configure_logging(cfg.telemetry.log_level)
    adapter = MockSpotAdapter()
    store = SQLiteStore(cfg.persistence.sqlite_path)
    start_bal = adapter.fetch_balances(cfg.market.symbol)
    ledgers = {
        "balances": BalanceLedger(BalanceSnapshot(start_bal.free_quote, start_bal.locked_quote, start_bal.free_base, start_bal.locked_base)),
        "inventory": InventoryLedger(InventorySnapshot(Decimal("0"), Decimal("0"))),
        "pnl": PnLLedger(PnLSnapshot(Decimal("0"), Decimal("0"))),
    }
    return GridEngine(cfg, adapter, store, ledgers, NullMetrics())
