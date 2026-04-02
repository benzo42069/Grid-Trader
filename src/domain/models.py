from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from domain.enums import (
    GridType,
    OrderStatus,
    OrderType,
    RuntimeMode,
    Side,
    SpacingType,
    TimeInForce,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class SymbolConstraints:
    symbol: str
    tick_size: Decimal
    step_size: Decimal
    min_qty: Decimal
    min_notional: Decimal
    supports_post_only: bool = True
    allowed_tif: tuple[TimeInForce, ...] = (TimeInForce.GTC,)


@dataclass(slots=True)
class MarketSnapshot:
    symbol: str
    bid: Decimal
    ask: Decimal
    ts: datetime = field(default_factory=utc_now)

    @property
    def mid(self) -> Decimal:
        return (self.bid + self.ask) / Decimal("2")


@dataclass(slots=True)
class OrderIntent:
    symbol: str
    side: Side
    price: Decimal
    quantity: Decimal
    client_order_id: str
    order_type: OrderType = OrderType.LIMIT
    time_in_force: TimeInForce = TimeInForce.GTC
    post_only: bool = True


@dataclass(slots=True)
class OpenOrder:
    symbol: str
    exchange_order_id: str
    client_order_id: str
    side: Side
    price: Decimal
    quantity: Decimal
    filled_qty: Decimal = Decimal("0")
    status: OrderStatus = OrderStatus.OPEN


@dataclass(slots=True)
class CancelRequest:
    symbol: str
    client_order_id: str


@dataclass(slots=True)
class CancelResult:
    client_order_id: str
    canceled: bool
    reason: str | None = None


@dataclass(slots=True)
class FillEvent:
    fill_id: str
    symbol: str
    client_order_id: str
    side: Side
    price: Decimal
    quantity: Decimal
    fee_quote: Decimal
    ts: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class BalanceSnapshot:
    free_quote: Decimal
    locked_quote: Decimal
    free_base: Decimal
    locked_base: Decimal


@dataclass(slots=True)
class InventorySnapshot:
    base_qty: Decimal
    avg_cost_quote_per_base: Decimal


@dataclass(slots=True)
class PnLSnapshot:
    realized_quote: Decimal
    fees_quote: Decimal


@dataclass(slots=True)
class MetaConfig:
    schema_version: str


@dataclass(slots=True)
class RuntimeConfig:
    mode: RuntimeMode
    arm_live_trading: bool


@dataclass(slots=True)
class ExchangeConfig:
    name: str
    credentials_env: str


@dataclass(slots=True)
class MarketConfig:
    symbol: str
    price_source: str


@dataclass(slots=True)
class StrategyConfig:
    grid_type: GridType
    spacing_type: SpacingType
    lower_price: Decimal
    upper_price: Decimal
    num_levels: int
    anchor_price_mode: str
    total_quote_allocation: Decimal
    per_level_sizing_mode: str
    post_only: bool
    time_in_force: TimeInForce


@dataclass(slots=True)
class RiskConfig:
    max_inventory_base: Decimal
    max_drawdown_pct: Decimal
    max_daily_loss_quote: Decimal
    max_reject_streak: int
    stale_market_data_seconds: int
    stale_private_stream_seconds: int
    max_reconciliation_mismatches: int


@dataclass(slots=True)
class PersistenceConfig:
    sqlite_path: str
    snapshot_interval_seconds: int


@dataclass(slots=True)
class TelemetryConfig:
    log_level: str


@dataclass(slots=True)
class EngineConfig:
    meta: MetaConfig
    runtime: RuntimeConfig
    exchange: ExchangeConfig
    market: MarketConfig
    strategy: StrategyConfig
    risk: RiskConfig
    persistence: PersistenceConfig
    telemetry: TelemetryConfig


@dataclass(slots=True)
class PersistedSnapshot:
    state: str
    balances: BalanceSnapshot
    inventory: InventorySnapshot
    pnl: PnLSnapshot
    open_orders: list[OpenOrder]
    ts: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class ReconciliationResult:
    consistent: list[str]
    missing_locally: list[str]
    missing_remotely: list[str]
    ambiguous: list[str]
    orphan_exchange_orders: list[str]

    @property
    def mismatch_count(self) -> int:
        return len(self.missing_locally) + len(self.missing_remotely) + len(self.ambiguous) + len(self.orphan_exchange_orders)


@dataclass(slots=True)
class DomainEvent:
    name: str
    payload: dict[str, Any]
    ts: datetime = field(default_factory=utc_now)

    def to_record(self) -> dict[str, Any]:
        return {"name": self.name, "payload": self.payload, "ts": self.ts.isoformat()}


def serialize_dataclass(dc: Any) -> dict[str, Any]:
    return asdict(dc)
