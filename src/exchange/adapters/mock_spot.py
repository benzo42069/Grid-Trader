from __future__ import annotations

from collections import deque
from decimal import Decimal

from domain.enums import OrderStatus
from domain.errors import ValidationError
from domain.models import BalanceSnapshot, CancelResult, FillEvent, MarketSnapshot, OpenOrder, OrderIntent, SymbolConstraints
from exchange.base import SpotExchangeAdapter
from exchange.constraints import normalize_price_qty
from exchange.symbols import canonical_symbol, mock_spot_venue_symbol
from exchange.types import HealthStatus


class MockSpotAdapter(SpotExchangeAdapter):
    def __init__(self) -> None:
        self._constraints_by_symbol = {
            "XRP/USD": SymbolConstraints(
                symbol=mock_spot_venue_symbol("XRP/USD"),
                tick_size=Decimal("0.0001"),
                step_size=Decimal("0.1"),
                min_qty=Decimal("0.1"),
                min_notional=Decimal("5"),
                supports_post_only=True,
            ),
            "DOGE/USD": SymbolConstraints(
                symbol=mock_spot_venue_symbol("DOGE/USD"),
                tick_size=Decimal("0.00001"),
                step_size=Decimal("1"),
                min_qty=Decimal("1"),
                min_notional=Decimal("5"),
                supports_post_only=True,
            ),
        }
        self.orders: dict[str, OpenOrder] = {}
        self.fills: deque[FillEvent] = deque()
        self.balance = BalanceSnapshot(
            free_quote=Decimal("100000"),
            locked_quote=Decimal("0"),
            free_base=Decimal("10000"),
            locked_base=Decimal("0"),
        )
        self.market_by_symbol = {
            "XRP/USD": MarketSnapshot(symbol="XRP/USD", bid=Decimal("0.5990"), ask=Decimal("0.6010")),
            "DOGE/USD": MarketSnapshot(symbol="DOGE/USD", bid=Decimal("0.1695"), ask=Decimal("0.1705")),
        }

    def load_symbol_constraints(self, symbol: str) -> SymbolConstraints:
        canonical = self._assert_symbol(symbol)
        return self._constraints_by_symbol[canonical]

    def fetch_balances(self, symbol: str) -> BalanceSnapshot:
        self._assert_symbol(symbol)
        return self.balance

    def fetch_open_orders(self, symbol: str) -> list[OpenOrder]:
        self._assert_symbol(symbol)
        return [o for o in self.orders.values() if o.status == OrderStatus.OPEN]

    def fetch_recent_fills(self, symbol: str) -> list[FillEvent]:
        self._assert_symbol(symbol)
        return list(self.fills)

    def place_managed_order_intent(self, intent: OrderIntent) -> OpenOrder:
        constraints = self.load_symbol_constraints(intent.symbol)
        if intent.post_only and not constraints.supports_post_only:
            raise ValidationError("post_only requested but unsupported")
        if intent.time_in_force not in constraints.allowed_tif:
            raise ValidationError("unsupported time_in_force")
        n_price, n_qty = normalize_price_qty(intent.price, intent.quantity, constraints)
        order = OpenOrder(
            symbol=intent.symbol,
            exchange_order_id=f"ex-{intent.client_order_id}",
            client_order_id=intent.client_order_id,
            side=intent.side,
            price=n_price,
            quantity=n_qty,
        )
        self.orders[intent.client_order_id] = order
        return order

    def cancel_managed_order(self, symbol: str, client_order_id: str) -> CancelResult:
        self._assert_symbol(symbol)
        order = self.orders.get(client_order_id)
        if not order:
            return CancelResult(client_order_id=client_order_id, canceled=False, reason="not_found")
        order.status = OrderStatus.CANCELED
        return CancelResult(client_order_id=client_order_id, canceled=True)

    def cancel_all_managed_orders(self, symbol: str) -> list[CancelResult]:
        self._assert_symbol(symbol)
        return [self.cancel_managed_order(symbol, cid) for cid in list(self.orders.keys())]

    def read_market_data(self, symbol: str) -> MarketSnapshot:
        canonical = self._assert_symbol(symbol)
        return self.market_by_symbol[canonical]

    def read_private_updates(self, symbol: str) -> list[FillEvent]:
        self._assert_symbol(symbol)
        out = list(self.fills)
        self.fills.clear()
        return out

    def health_check(self) -> HealthStatus:
        return HealthStatus(market_data_ok=True, private_stream_ok=True)

    def inject_fill(self, fill: FillEvent) -> None:
        self.fills.append(fill)
        if fill.client_order_id in self.orders:
            self.orders[fill.client_order_id].status = OrderStatus.FILLED

    def _assert_symbol(self, symbol: str) -> str:
        canonical = canonical_symbol(symbol)
        if canonical not in self._constraints_by_symbol:
            raise ValidationError(f"unsupported symbol {symbol}")
        return canonical
