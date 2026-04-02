from decimal import Decimal

import pytest

from domain.ids import deterministic_client_order_id
from domain.models import SymbolConstraints
from exchange.constraints import normalize_price_qty


def test_client_order_id_determinism():
    a = deterministic_client_order_id("BTC-USDT", "buy", 1, 2)
    b = deterministic_client_order_id("BTC-USDT", "buy", 1, 2)
    assert a == b


def test_normalization_notional_fail():
    c = SymbolConstraints("BTC-USDT", Decimal("0.1"), Decimal("0.01"), Decimal("0.01"), Decimal("100"))
    with pytest.raises(Exception):
        normalize_price_qty(Decimal("1"), Decimal("1"), c)
