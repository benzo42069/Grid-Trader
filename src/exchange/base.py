from __future__ import annotations

from abc import ABC, abstractmethod

from domain.models import (
    BalanceSnapshot,
    CancelResult,
    FillEvent,
    MarketSnapshot,
    OpenOrder,
    OrderIntent,
    SymbolConstraints,
)
from exchange.types import HealthStatus


class SpotExchangeAdapter(ABC):
    @abstractmethod
    def load_symbol_constraints(self, symbol: str) -> SymbolConstraints: ...

    @abstractmethod
    def fetch_balances(self, symbol: str) -> BalanceSnapshot: ...

    @abstractmethod
    def fetch_open_orders(self, symbol: str) -> list[OpenOrder]: ...

    @abstractmethod
    def fetch_recent_fills(self, symbol: str) -> list[FillEvent]: ...

    @abstractmethod
    def place_managed_order_intent(self, intent: OrderIntent) -> OpenOrder: ...

    @abstractmethod
    def cancel_managed_order(self, symbol: str, client_order_id: str) -> CancelResult: ...

    @abstractmethod
    def cancel_all_managed_orders(self, symbol: str) -> list[CancelResult]: ...

    @abstractmethod
    def read_market_data(self, symbol: str) -> MarketSnapshot: ...

    @abstractmethod
    def read_private_updates(self, symbol: str) -> list[FillEvent]: ...

    @abstractmethod
    def health_check(self) -> HealthStatus: ...
