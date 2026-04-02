from __future__ import annotations

from domain.errors import ValidationError


_ALLOWED_SEPARATORS = ("/", "-", "_")


def canonical_symbol(symbol: str) -> str:
    """Normalize symbol into canonical BASE/QUOTE representation."""
    raw = symbol.strip().upper()
    for sep in _ALLOWED_SEPARATORS:
        if sep in raw:
            base, quote = raw.split(sep, 1)
            if not base or not quote:
                break
            return f"{base}/{quote}"
    raise ValidationError(f"unsupported symbol format: {symbol}")


def mock_spot_venue_symbol(symbol: str) -> str:
    canonical = canonical_symbol(symbol)
    base, quote = canonical.split("/", 1)
    return f"{base}-{quote}"
