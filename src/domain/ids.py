from __future__ import annotations

import hashlib


def deterministic_client_order_id(symbol: str, side: str, level_index: int, cycle: int) -> str:
    raw = f"{symbol}|{side}|{level_index}|{cycle}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"g1-{digest}"
