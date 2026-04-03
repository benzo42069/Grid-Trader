from __future__ import annotations

import os
from decimal import Decimal

from domain.enums import RuntimeMode
from domain.errors import ValidationError
from exchange.symbols import canonical_symbol


def _d(v: str) -> Decimal:
    return Decimal(v)


def semantic_validate(raw: dict, env: dict[str, str] | None = None) -> None:
    env_map = os.environ if env is None else env

    if raw["meta"]["schema_version"] != "1.0.0":
        raise ValidationError("unsupported schema_version")

    s = raw["strategy"]
    r = raw["risk"]
    mode = RuntimeMode(raw["runtime"]["mode"])
    exchange_name = raw["exchange"]["name"].lower()
    canonical_symbol(raw["market"]["symbol"])

    if _d(s["lower_price"]) >= _d(s["upper_price"]):
        raise ValidationError("lower_price must be < upper_price")
    if int(s["num_levels"]) < 2:
        raise ValidationError("num_levels must be >= 2")
    if _d(s["total_quote_allocation"]) <= 0:
        raise ValidationError("total_quote_allocation must be > 0")

    for key in ["max_inventory_base", "max_drawdown_pct", "max_daily_loss_quote"]:
        if _d(r[key]) <= 0:
            raise ValidationError(f"{key} must be > 0")
    if int(r["max_open_orders"]) < 1:
        raise ValidationError("max_open_orders must be >= 1")
    if _d(r["max_drawdown_pct"]) > Decimal("100"):
        raise ValidationError("max_drawdown_pct must be <= 100")

    if mode == RuntimeMode.LIVE and not raw["runtime"]["arm_live_trading"]:
        raise ValidationError("live mode requires arm_live_trading=true")

    if mode == RuntimeMode.LIVE and exchange_name == "kraken":
        if not env_map.get("KRAKEN_API_KEY") or not env_map.get("KRAKEN_API_SECRET"):
            raise ValidationError("missing KRAKEN_API_KEY/KRAKEN_API_SECRET for live mode")
    elif mode == RuntimeMode.LIVE:
        cred_var = raw["exchange"].get("credentials_env", "")
        if cred_var and not env_map.get(cred_var):
            raise ValidationError(f"missing live credentials in env var {cred_var}")


    if s["time_in_force"] != "GTC":
        raise ValidationError("only GTC is supported in MVP")
