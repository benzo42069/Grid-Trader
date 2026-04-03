from __future__ import annotations

from domain.enums import EngineState, RuntimeMode, Side
from domain.models import FillEvent, PersistedSnapshot
from domain.errors import ValidationError
from execution.fill_processor import FillProcessor
from execution.order_manager import OrderManager
from execution.reconciliation import reconcile
from market_data.service import MarketDataService
from risk.manager import RiskManager
from strategy.grid_planner import plan_initial_grid
from strategy.state_machine import EngineStateMachine


class GridEngine:
    def __init__(self, cfg, adapter, store, ledgers, telemetry) -> None:
        self.cfg = cfg
        self.adapter = adapter
        self.store = store
        self.telemetry = telemetry
        self.state = EngineStateMachine()
        self.order_manager = OrderManager(
            adapter,
            ledgers["balances"],
            store,
            max_open_orders=cfg.risk.max_open_orders,
        )
        self.fill_processor = FillProcessor(ledgers, store)
        self.market_data = MarketDataService(adapter, cfg.market.symbol)
        self.risk = RiskManager(cfg.risk, ledgers, self.market_data.cache)

    def bootstrap(self) -> None:
        self.state.transition(EngineState.VALIDATING_CONFIG)
        self.store.journal("config_loaded", {"config_hash": self.cfg.meta.config_hash})
        self.state.transition(EngineState.LOADING_METADATA)
        constraints = self.adapter.load_symbol_constraints(self.cfg.market.symbol)
        if not self.store.is_healthy():
            self.stop("persistence unavailable")
            return
        self.store.journal("metadata_loaded", {"symbol": self.cfg.market.symbol})
        self.state.transition(EngineState.RECONCILING)
        rec = reconcile(self.store.load_snapshot(), self.adapter.fetch_open_orders(self.cfg.market.symbol))
        self.store.journal("reconciliation_completed", {"mismatches": rec.mismatch_count})
        if rec.mismatch_count > self.cfg.risk.max_reconciliation_mismatches:
            self.stop("reconciliation mismatch")
            return
        health = self.adapter.health_check()
        if not health.market_data_ok or not health.private_stream_ok:
            self.stop("exchange stream unhealthy")
            return

        armed = EngineState.ARMED_LIVE if self.cfg.runtime.mode == RuntimeMode.LIVE else EngineState.ARMED_PAPER
        self.state.transition(armed)
        self.state.transition(EngineState.PLACING_INITIAL_GRID)
        market = self.market_data.poll()
        if market is None:
            self.stop("market data unavailable")
            return
        for intent in plan_initial_grid(self.cfg, market, constraints):
            if self.risk.check():
                self.stop("risk gate failed before order submit")
                return
            try:
                self.order_manager.submit(intent)
            except ValidationError as exc:
                self.stop(f"order submit blocked: {exc}")
                return
        self.store.write_snapshot(
            PersistedSnapshot(
                state=EngineState.RUNNING.value,
                balances=self.fill_processor.balance.snapshot,
                inventory=self.fill_processor.inventory.snapshot,
                pnl=self.fill_processor.pnl.snapshot,
                open_orders=self.adapter.fetch_open_orders(self.cfg.market.symbol),
                config_hash=self.cfg.meta.config_hash,
            )
        )
        self.state.transition(EngineState.RUNNING)

    def on_private_updates(self) -> None:
        self.risk.note_private_stream_heartbeat()
        health = self.adapter.health_check()
        if not health.private_stream_ok:
            self.stop("private stream disconnected")
            return
        for fill in self.adapter.read_private_updates(self.cfg.market.symbol):
            self.fill_processor.process(fill)

    def run_risk_checks(self) -> None:
        reason = self.risk.check()
        if reason:
            self.stop(reason.value)

    def stop(self, reason: str) -> None:
        self.state.transition(EngineState.STOPPING)
        self.order_manager.cancel_all(self.cfg.market.symbol)
        self.store.journal("risk_stop_triggered", {"reason": reason})
        self.state.transition(EngineState.STOPPED)

    def schedule_counter_order(self, fill: FillEvent):
        side = Side.SELL if fill.side == Side.BUY else Side.BUY
        return side
