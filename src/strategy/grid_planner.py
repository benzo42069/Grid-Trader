from __future__ import annotations

from decimal import Decimal

from domain.enums import Side, SpacingType
from domain.errors import ValidationError
from domain.models import EngineConfig, MarketSnapshot, OrderIntent, SymbolConstraints
from domain.ids import deterministic_client_order_id
from exchange.constraints import normalize_price_qty
from strategy.grid_math import arithmetic_levels, geometric_levels


def generate_levels(cfg: EngineConfig) -> list[Decimal]:
    s = cfg.strategy
    if s.spacing_type == SpacingType.ARITHMETIC:
        return arithmetic_levels(s.lower_price, s.upper_price, s.num_levels)
    return geometric_levels(s.lower_price, s.upper_price, s.num_levels)


def plan_initial_grid(cfg: EngineConfig, market: MarketSnapshot, constraints: SymbolConstraints, cycle: int = 0) -> list[OrderIntent]:
    levels = generate_levels(cfg)
    per_level_quote = cfg.strategy.total_quote_allocation / Decimal(len(levels))
    planned: list[OrderIntent] = []
    seen: set[Decimal] = set()

    for i, level in enumerate(levels):
        side = Side.BUY if level < market.mid else Side.SELL
        qty = per_level_quote / level
        n_price, n_qty = normalize_price_qty(level, qty, constraints)
        if n_price in seen:
            raise ValidationError("normalization collapsed distinct levels")
        seen.add(n_price)
        planned.append(
            OrderIntent(
                symbol=cfg.market.symbol,
                side=side,
                price=n_price,
                quantity=n_qty,
                client_order_id=deterministic_client_order_id(cfg.market.symbol, side.value, i, cycle),
                post_only=cfg.strategy.post_only,
                time_in_force=cfg.strategy.time_in_force,
            )
        )
    return planned
