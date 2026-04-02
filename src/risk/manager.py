from __future__ import annotations

from decimal import Decimal

from domain.enums import RiskStopReason
from market_data.health import is_stale
from risk.kill_switch import KillSwitch
from risk.rules import check_inventory


class RiskManager:
    def __init__(self, cfg, ledgers, market_cache) -> None:
        self.cfg = cfg
        self.ledgers = ledgers
        self.market_cache = market_cache
        self.kill_switch = KillSwitch()
        self.reject_streak = 0

    def check(self):
        inv = check_inventory(self.cfg.max_inventory_base, self.ledgers["inventory"].snapshot.base_qty)
        if inv:
            self.kill_switch.trigger(inv)
            return inv

        if self.ledgers["pnl"].snapshot.realized_quote <= -self.cfg.max_daily_loss_quote:
            self.kill_switch.trigger(RiskStopReason.MAX_DAILY_LOSS)
            return RiskStopReason.MAX_DAILY_LOSS

        if is_stale(self.market_cache.last, self.cfg.stale_market_data_seconds):
            self.kill_switch.trigger(RiskStopReason.STALE_MARKET)
            return RiskStopReason.STALE_MARKET

        return None

    def register_reject(self):
        self.reject_streak += 1
        if self.reject_streak >= self.cfg.max_reject_streak:
            self.kill_switch.trigger(RiskStopReason.MAX_REJECT_STREAK)
            return RiskStopReason.MAX_REJECT_STREAK
        return None
