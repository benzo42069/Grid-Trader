from __future__ import annotations

from domain.models import MarketSnapshot


class MarketDataCache:
    def __init__(self) -> None:
        self.last: MarketSnapshot | None = None

    def update(self, snap: MarketSnapshot) -> None:
        self.last = snap
