from decimal import Decimal
from datetime import datetime, timedelta, timezone

from domain.models import BalanceSnapshot, InventorySnapshot, OpenOrder, PersistedSnapshot, PnLSnapshot, ReconciliationResult
from domain.models import MarketSnapshot
from execution.reconciliation import reconcile
from ledger.balances import BalanceLedger
from ledger.inventory import InventoryLedger
from ledger.pnl import PnLLedger
from risk.manager import RiskManager


class DummyCache:
    last = None


class DummyCfg:
    max_inventory_base = Decimal("1")
    max_daily_loss_quote = Decimal("100")
    stale_market_data_seconds = 1
    stale_private_stream_seconds = 1
    max_reject_streak = 2


def test_risk_stale_market_trigger():
    ledgers = {
        "balances": BalanceLedger(BalanceSnapshot(Decimal("1"), Decimal("0"), Decimal("0"), Decimal("0"))),
        "inventory": InventoryLedger(InventorySnapshot(Decimal("0"), Decimal("0"))),
        "pnl": PnLLedger(PnLSnapshot(Decimal("0"), Decimal("0"))),
    }
    r = RiskManager(DummyCfg(), ledgers, DummyCache())
    assert r.check() is not None


def test_risk_stale_private_stream_trigger():
    ledgers = {
        "balances": BalanceLedger(BalanceSnapshot(Decimal("1"), Decimal("0"), Decimal("0"), Decimal("0"))),
        "inventory": InventoryLedger(InventorySnapshot(Decimal("0"), Decimal("0"))),
        "pnl": PnLLedger(PnLSnapshot(Decimal("0"), Decimal("0"))),
    }
    cache = DummyCache()
    cache.last = MarketSnapshot(symbol="XRP/USD", bid=Decimal("1"), ask=Decimal("1.1"))
    r = RiskManager(DummyCfg(), ledgers, cache)
    r.last_private_update_ts = datetime.now(timezone.utc) - timedelta(seconds=10)
    assert r.check() is not None


def test_reconciliation_classification():
    snap = PersistedSnapshot(
        state="RUNNING",
        balances=BalanceSnapshot(Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0")),
        inventory=InventorySnapshot(Decimal("0"), Decimal("0")),
        pnl=PnLSnapshot(Decimal("0"), Decimal("0")),
        open_orders=[OpenOrder("BTC-USDT", "1", "cid1", "buy", Decimal("1"), Decimal("1"))],
    )
    result: ReconciliationResult = reconcile(snap, [])
    assert "cid1" in result.missing_remotely
