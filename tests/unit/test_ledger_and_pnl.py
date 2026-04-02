from decimal import Decimal

from domain.enums import Side
from domain.models import BalanceSnapshot, FillEvent, InventorySnapshot, PnLSnapshot
from ledger.balances import BalanceLedger
from ledger.inventory import InventoryLedger
from ledger.pnl import PnLLedger


def test_fill_accounting_realized_pnl_sell():
    b = BalanceLedger(BalanceSnapshot(Decimal("1000"), Decimal("0"), Decimal("0"), Decimal("1")))
    i = InventoryLedger(InventorySnapshot(Decimal("1"), Decimal("100")))
    p = PnLLedger(PnLSnapshot(Decimal("0"), Decimal("0")))
    fill = FillEvent("f1", "BTC-USDT", "cid", Side.SELL, Decimal("120"), Decimal("1"), Decimal("1"))
    b.apply_fill(fill)
    realized = i.apply_fill(fill)
    p.apply_trade(realized, fill.fee_quote)
    assert p.snapshot.realized_quote == Decimal("20")
    assert p.snapshot.fees_quote == Decimal("1")
