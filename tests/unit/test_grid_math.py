from decimal import Decimal

from strategy.grid_math import arithmetic_levels, geometric_levels


def test_arithmetic_levels():
    out = arithmetic_levels(Decimal("10"), Decimal("20"), 3)
    assert out == [Decimal("10"), Decimal("15"), Decimal("20")]


def test_geometric_levels():
    out = geometric_levels(Decimal("10"), Decimal("40"), 3)
    assert out[0] == Decimal("10")
    assert out[-1].quantize(Decimal("0.0001")) == Decimal("40.0000")
