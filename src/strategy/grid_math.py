from __future__ import annotations

from decimal import Decimal, getcontext

getcontext().prec = 28


def arithmetic_levels(lower: Decimal, upper: Decimal, num_levels: int) -> list[Decimal]:
    step = (upper - lower) / Decimal(num_levels - 1)
    return [lower + (step * Decimal(i)) for i in range(num_levels)]


def geometric_levels(lower: Decimal, upper: Decimal, num_levels: int) -> list[Decimal]:
    ratio = (upper / lower) ** (Decimal("1") / Decimal(num_levels - 1))
    return [lower * (ratio ** Decimal(i)) for i in range(num_levels)]
