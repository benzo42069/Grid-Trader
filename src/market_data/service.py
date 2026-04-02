from exchange.base import SpotExchangeAdapter
from market_data.cache import MarketDataCache


class MarketDataService:
    def __init__(self, adapter: SpotExchangeAdapter, symbol: str) -> None:
        self.adapter = adapter
        self.symbol = symbol
        self.cache = MarketDataCache()

    def poll(self):
        snap = self.adapter.read_market_data(self.symbol)
        self.cache.update(snap)
        return snap
