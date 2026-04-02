from __future__ import annotations

from domain.models import FillEvent


class FillProcessor:
    def __init__(self, ledgers, store) -> None:
        self.balance = ledgers["balances"]
        self.inventory = ledgers["inventory"]
        self.pnl = ledgers["pnl"]
        self.store = store
        self._seen_fill_ids: set[str] = set()

    def process(self, fill: FillEvent) -> bool:
        if fill.fill_id in self._seen_fill_ids:
            return False
        self._seen_fill_ids.add(fill.fill_id)
        self.balance.apply_fill(fill)
        realized = self.inventory.apply_fill(fill)
        self.pnl.apply_trade(realized_quote=realized, fee_quote=fill.fee_quote)
        self.store.journal("fill_processed", {"fill_id": fill.fill_id, "cid": fill.client_order_id})
        return True
