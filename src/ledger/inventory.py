from __future__ import annotations

from decimal import Decimal

from domain.enums import Side
from domain.models import FillEvent, InventorySnapshot


class InventoryLedger:
    def __init__(self, snapshot: InventorySnapshot) -> None:
        self.snapshot = snapshot

    def apply_fill(self, fill: FillEvent) -> Decimal:
        if fill.side == Side.BUY:
            total_cost = (self.snapshot.avg_cost_quote_per_base * self.snapshot.base_qty) + (fill.price * fill.quantity)
            new_qty = self.snapshot.base_qty + fill.quantity
            self.snapshot.base_qty = new_qty
            self.snapshot.avg_cost_quote_per_base = total_cost / new_qty
            return Decimal("0")

        sell_qty = fill.quantity
        realized = (fill.price - self.snapshot.avg_cost_quote_per_base) * sell_qty
        self.snapshot.base_qty -= sell_qty
        if self.snapshot.base_qty <= Decimal("0"):
            self.snapshot.base_qty = Decimal("0")
            self.snapshot.avg_cost_quote_per_base = Decimal("0")
        return realized
