from exchange.base import SpotExchangeAdapter
from market_data.cache import MarketDataCache


class MarketDataService:
    def __init__(self, adapter: SpotExchangeAdapter, symbol: str) -> None:
        self.adapter = adapter
        self.symbol = symbol
        self.cache = MarketDataCache()
        self.consecutive_failures = 0

    def poll(self):
        health = self.adapter.health_check()
        if not health.market_data_ok:
            self.consecutive_failures += 1
            return self.cache.last
        snap = self.adapter.read_market_data(self.symbol)
        self.consecutive_failures = 0
        self.cache.update(snap)
        return snap
