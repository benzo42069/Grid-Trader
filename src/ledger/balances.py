from __future__ import annotations

from decimal import Decimal

from domain.enums import Side
from domain.errors import ValidationError
from domain.models import BalanceSnapshot, FillEvent, OrderIntent


class BalanceLedger:
    def __init__(self, snapshot: BalanceSnapshot) -> None:
        self.snapshot = snapshot

    def reserve_for_order(self, intent: OrderIntent) -> None:
        if intent.side == Side.BUY:
            needed = intent.price * intent.quantity
            if self.snapshot.free_quote < needed:
                raise ValidationError("insufficient free quote")
            self.snapshot.free_quote -= needed
            self.snapshot.locked_quote += needed
        else:
            if self.snapshot.free_base < intent.quantity:
                raise ValidationError("insufficient free base")
            self.snapshot.free_base -= intent.quantity
            self.snapshot.locked_base += intent.quantity

    def release_for_cancel(self, intent: OrderIntent) -> None:
        if intent.side == Side.BUY:
            locked = intent.price * intent.quantity
            self.snapshot.locked_quote -= locked
            self.snapshot.free_quote += locked
        else:
            self.snapshot.locked_base -= intent.quantity
            self.snapshot.free_base += intent.quantity

    def apply_fill(self, fill: FillEvent) -> None:
        notional = fill.price * fill.quantity
        if fill.side == Side.BUY:
            self.snapshot.locked_quote -= notional
            self.snapshot.free_base += fill.quantity
            self.snapshot.free_quote -= fill.fee_quote
        else:
            self.snapshot.locked_base -= fill.quantity
            self.snapshot.free_quote += (notional - fill.fee_quote)
