from __future__ import annotations

from enum import Enum


class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    NEW = "new"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


class OrderType(str, Enum):
    LIMIT = "limit"


class TimeInForce(str, Enum):
    GTC = "GTC"


class EngineState(str, Enum):
    BOOTSTRAP = "BOOTSTRAP"
    VALIDATING_CONFIG = "VALIDATING_CONFIG"
    LOADING_METADATA = "LOADING_METADATA"
    RECONCILING = "RECONCILING"
    ARMED_PAPER = "ARMED_PAPER"
    ARMED_LIVE = "ARMED_LIVE"
    PLACING_INITIAL_GRID = "PLACING_INITIAL_GRID"
    RUNNING = "RUNNING"
    PAUSED_RISK = "PAUSED_RISK"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


class RuntimeMode(str, Enum):
    PAPER = "paper"
    LIVE = "live"


class SpacingType(str, Enum):
    ARITHMETIC = "arithmetic"
    GEOMETRIC = "geometric"


class GridType(str, Enum):
    STATIC_NEUTRAL = "static_neutral"


class RiskStopReason(str, Enum):
    MAX_INVENTORY = "max_inventory"
    MAX_DRAWDOWN = "max_drawdown"
    MAX_DAILY_LOSS = "max_daily_loss"
    MAX_REJECT_STREAK = "max_reject_streak"
    STALE_MARKET = "stale_market"
    STALE_PRIVATE = "stale_private"
    RECONCILIATION_MISMATCH = "reconciliation_mismatch"
    DUPLICATE_ORDER = "duplicate_order"
    PERSISTENCE_FAILURE = "persistence_failure"
    AMBIGUOUS_EXECUTION = "ambiguous_execution"
