from __future__ import annotations

from domain.errors import AmbiguousExchangeError, ValidationError
from domain.models import OrderIntent


class OrderManager:
    def __init__(self, adapter, balance_ledger, store) -> None:
        self.adapter = adapter
        self.balance_ledger = balance_ledger
        self.store = store
        self.inflight: set[str] = set()
        self.active_client_order_ids: set[str] = set()

    def submit(self, intent: OrderIntent):
        if intent.client_order_id in self.inflight or intent.client_order_id in self.active_client_order_ids:
            raise ValidationError("duplicate client order id")
        self.balance_ledger.reserve_for_order(intent)
        self.store.journal("order_intent_created", {"cid": intent.client_order_id})
        self.inflight.add(intent.client_order_id)
        try:
            order = self.adapter.place_managed_order_intent(intent)
            self.store.journal("order_submit_accepted", {"cid": intent.client_order_id})
            self.active_client_order_ids.add(intent.client_order_id)
            return order
        except AmbiguousExchangeError:
            self.store.journal("order_submit_rejected", {"cid": intent.client_order_id, "kind": "ambiguous"})
            raise
        finally:
            self.inflight.remove(intent.client_order_id)

    def cancel(self, symbol: str, intent: OrderIntent):
        res = self.adapter.cancel_managed_order(symbol, intent.client_order_id)
        if res.canceled:
            self.balance_ledger.release_for_cancel(intent)
            self.active_client_order_ids.discard(intent.client_order_id)
            self.store.journal("order_canceled", {"cid": intent.client_order_id})
        return res

    def cancel_all(self, symbol: str):
        return self.adapter.cancel_all_managed_orders(symbol)
