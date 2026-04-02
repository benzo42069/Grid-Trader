from __future__ import annotations

from datetime import datetime, timezone

from domain.models import MarketSnapshot


def is_stale(snapshot: MarketSnapshot | None, threshold_seconds: int) -> bool:
    if snapshot is None:
        return True
    age = (datetime.now(timezone.utc) - snapshot.ts).total_seconds()
    return age > threshold_seconds
