from __future__ import annotations

from decimal import Decimal

from domain.enums import GridType, RuntimeMode, SpacingType, TimeInForce
from domain.models import (
    EngineConfig,
    ExchangeConfig,
    MarketConfig,
    MetaConfig,
    PersistenceConfig,
    RiskConfig,
    RuntimeConfig,
    StrategyConfig,
    TelemetryConfig,
)


def normalize_config(raw: dict) -> EngineConfig:
    return EngineConfig(
        meta=MetaConfig(schema_version=raw["meta"]["schema_version"]),
        runtime=RuntimeConfig(
            mode=RuntimeMode(raw["runtime"]["mode"]),
            arm_live_trading=raw["runtime"]["arm_live_trading"],
        ),
        exchange=ExchangeConfig(**raw["exchange"]),
        market=MarketConfig(**raw["market"]),
        strategy=StrategyConfig(
            grid_type=GridType(raw["strategy"]["grid_type"]),
            spacing_type=SpacingType(raw["strategy"]["spacing_type"]),
            lower_price=Decimal(raw["strategy"]["lower_price"]),
            upper_price=Decimal(raw["strategy"]["upper_price"]),
            num_levels=raw["strategy"]["num_levels"],
            anchor_price_mode=raw["strategy"]["anchor_price_mode"],
            total_quote_allocation=Decimal(raw["strategy"]["total_quote_allocation"]),
            per_level_sizing_mode=raw["strategy"]["per_level_sizing_mode"],
            post_only=raw["strategy"]["post_only"],
            time_in_force=TimeInForce(raw["strategy"]["time_in_force"]),
        ),
        risk=RiskConfig(
            max_inventory_base=Decimal(raw["risk"]["max_inventory_base"]),
            max_drawdown_pct=Decimal(raw["risk"]["max_drawdown_pct"]),
            max_daily_loss_quote=Decimal(raw["risk"]["max_daily_loss_quote"]),
            max_reject_streak=raw["risk"]["max_reject_streak"],
            stale_market_data_seconds=raw["risk"]["stale_market_data_seconds"],
            stale_private_stream_seconds=raw["risk"]["stale_private_stream_seconds"],
            max_reconciliation_mismatches=raw["risk"]["max_reconciliation_mismatches"],
        ),
        persistence=PersistenceConfig(**raw["persistence"]),
        telemetry=TelemetryConfig(**raw["telemetry"]),
    )
