from __future__ import annotations

from collections import deque
from decimal import Decimal

from domain.enums import OrderStatus
from domain.models import BalanceSnapshot, CancelResult, FillEvent, MarketSnapshot, OpenOrder, OrderIntent, SymbolConstraints
from exchange.base import SpotExchangeAdapter
from exchange.types import HealthStatus


class MockSpotAdapter(SpotExchangeAdapter):
    def __init__(self) -> None:
        self.constraints = SymbolConstraints(
            symbol="BTC-USDT",
            tick_size=Decimal("0.1"),
            step_size=Decimal("0.0001"),
            min_qty=Decimal("0.0001"),
            min_notional=Decimal("5"),
            supports_post_only=True,
        )
        self.orders: dict[str, OpenOrder] = {}
        self.fills: deque[FillEvent] = deque()
        self.balance = BalanceSnapshot(
            free_quote=Decimal("100000"),
            locked_quote=Decimal("0"),
            free_base=Decimal("1"),
            locked_base=Decimal("0"),
        )
        self.market = MarketSnapshot(symbol="BTC-USDT", bid=Decimal("29999"), ask=Decimal("30001"))

    def load_symbol_constraints(self, symbol: str) -> SymbolConstraints:
        return self.constraints

    def fetch_balances(self, symbol: str) -> BalanceSnapshot:
        return self.balance

    def fetch_open_orders(self, symbol: str) -> list[OpenOrder]:
        return [o for o in self.orders.values() if o.status == OrderStatus.OPEN]

    def fetch_recent_fills(self, symbol: str) -> list[FillEvent]:
        return list(self.fills)

    def place_managed_order_intent(self, intent: OrderIntent) -> OpenOrder:
        order = OpenOrder(
            symbol=intent.symbol,
            exchange_order_id=f"ex-{intent.client_order_id}",
            client_order_id=intent.client_order_id,
            side=intent.side,
            price=intent.price,
            quantity=intent.quantity,
        )
        self.orders[intent.client_order_id] = order
        return order

    def cancel_managed_order(self, symbol: str, client_order_id: str) -> CancelResult:
        order = self.orders.get(client_order_id)
        if not order:
            return CancelResult(client_order_id=client_order_id, canceled=False, reason="not_found")
        order.status = OrderStatus.CANCELED
        return CancelResult(client_order_id=client_order_id, canceled=True)

    def cancel_all_managed_orders(self, symbol: str) -> list[CancelResult]:
        return [self.cancel_managed_order(symbol, cid) for cid in list(self.orders.keys())]

    def read_market_data(self, symbol: str) -> MarketSnapshot:
        return self.market

    def read_private_updates(self, symbol: str) -> list[FillEvent]:
        out = list(self.fills)
        self.fills.clear()
        return out

    def health_check(self) -> HealthStatus:
        return HealthStatus(market_data_ok=True, private_stream_ok=True)

    def inject_fill(self, fill: FillEvent) -> None:
        self.fills.append(fill)
        if fill.client_order_id in self.orders:
            self.orders[fill.client_order_id].status = OrderStatus.FILLED
