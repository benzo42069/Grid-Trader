from decimal import Decimal

import pytest

from domain.enums import Side
from domain.errors import ValidationError
from domain.models import BalanceSnapshot, OrderIntent
from execution.order_manager import OrderManager
from ledger.balances import BalanceLedger


class DummyStore:
    def journal(self, *_args, **_kwargs):
        return None


class DummyAdapter:
    def place_managed_order_intent(self, intent):
        return intent

    def cancel_managed_order(self, symbol, client_order_id):
        class R:
            canceled = True

        return R()

    def cancel_all_managed_orders(self, symbol):
        return []


def test_duplicate_logical_order_prevented():
    ledger = BalanceLedger(BalanceSnapshot(Decimal("1000"), Decimal("0"), Decimal("1000"), Decimal("0")))
    manager = OrderManager(DummyAdapter(), ledger, DummyStore())
    intent = OrderIntent(
        symbol="XRP/USD",
        side=Side.BUY,
        price=Decimal("1"),
        quantity=Decimal("10"),
        client_order_id="dup-1",
    )

    manager.submit(intent)
    with pytest.raises(ValidationError):
        manager.submit(intent)
