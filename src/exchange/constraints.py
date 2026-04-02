from __future__ import annotations

from decimal import Decimal, ROUND_DOWN

from domain.errors import ValidationError
from domain.models import SymbolConstraints


def quantize_to_step(value: Decimal, step: Decimal) -> Decimal:
    return (value / step).to_integral_value(rounding=ROUND_DOWN) * step


def normalize_price_qty(price: Decimal, qty: Decimal, constraints: SymbolConstraints) -> tuple[Decimal, Decimal]:
    n_price = quantize_to_step(price, constraints.tick_size)
    n_qty = quantize_to_step(qty, constraints.step_size)
    if n_qty < constraints.min_qty:
        raise ValidationError("qty below min_qty")
    if n_price * n_qty < constraints.min_notional:
        raise ValidationError("notional below min_notional")
    return n_price, n_qty
