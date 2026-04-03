from __future__ import annotations

from domain.enums import OrderStatus
from domain.models import OpenOrder, PersistedSnapshot, ReconciliationResult


def reconcile(snapshot: PersistedSnapshot | None, exchange_open_orders: list[OpenOrder]) -> ReconciliationResult:
    if snapshot is None:
        return ReconciliationResult([], [], [], [], [])

    local_ids = {o.client_order_id for o in snapshot.open_orders}
    remote_ids = {o.client_order_id for o in exchange_open_orders}

    consistent = sorted(list(local_ids & remote_ids))
    missing_locally: list[str] = []
    missing_remotely = sorted(list(local_ids - remote_ids))
    orphan = sorted(list(remote_ids - local_ids))
    ambiguous = sorted(
        o.client_order_id for o in exchange_open_orders if o.status in {OrderStatus.UNKNOWN, OrderStatus.PARTIALLY_FILLED}
    )
    consistent = [cid for cid in consistent if cid not in set(ambiguous)]
    return ReconciliationResult(consistent, missing_locally, missing_remotely, ambiguous, orphan)
