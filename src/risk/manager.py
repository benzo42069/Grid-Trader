from __future__ import annotations

from datetime import datetime, timezone
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
        self.last_private_update_ts = datetime.now(timezone.utc)
        self.peak_realized_quote = Decimal("0")

    def check(self):
        inv = check_inventory(self.cfg.max_inventory_base, self.ledgers["inventory"].snapshot.base_qty)
        if inv:
            self.kill_switch.trigger(inv)
            return inv

        realized_quote = self.ledgers["pnl"].snapshot.realized_quote
        if realized_quote > self.peak_realized_quote:
            self.peak_realized_quote = realized_quote
        if self.peak_realized_quote > Decimal("0"):
            drawdown_pct = ((self.peak_realized_quote - realized_quote) / self.peak_realized_quote) * Decimal("100")
            if drawdown_pct >= self.cfg.max_drawdown_pct:
                self.kill_switch.trigger(RiskStopReason.MAX_DRAWDOWN)
                return RiskStopReason.MAX_DRAWDOWN

        if realized_quote <= -self.cfg.max_daily_loss_quote:
            self.kill_switch.trigger(RiskStopReason.MAX_DAILY_LOSS)
            return RiskStopReason.MAX_DAILY_LOSS

        if is_stale(self.market_cache.last, self.cfg.stale_market_data_seconds):
            self.kill_switch.trigger(RiskStopReason.STALE_MARKET)
            return RiskStopReason.STALE_MARKET
        private_age = (datetime.now(timezone.utc) - self.last_private_update_ts).total_seconds()
        if private_age > self.cfg.stale_private_stream_seconds:
            self.kill_switch.trigger(RiskStopReason.STALE_PRIVATE)
            return RiskStopReason.STALE_PRIVATE

        return None

    def register_reject(self):
        self.reject_streak += 1
        if self.reject_streak >= self.cfg.max_reject_streak:
            self.kill_switch.trigger(RiskStopReason.MAX_REJECT_STREAK)
            return RiskStopReason.MAX_REJECT_STREAK
        return None

    def note_private_stream_heartbeat(self) -> None:
        self.last_private_update_ts = datetime.now(timezone.utc)
