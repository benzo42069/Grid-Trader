from __future__ import annotations

from domain.enums import EngineState, RuntimeMode, Side
from domain.models import FillEvent
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
        self.order_manager = OrderManager(adapter, ledgers["balances"], store)
        self.fill_processor = FillProcessor(ledgers, store)
        self.market_data = MarketDataService(adapter, cfg.market.symbol)
        self.risk = RiskManager(cfg.risk, ledgers, self.market_data.cache)

    def bootstrap(self) -> None:
        self.state.transition(EngineState.VALIDATING_CONFIG)
        self.store.journal("config_loaded", {})
        self.state.transition(EngineState.LOADING_METADATA)
        constraints = self.adapter.load_symbol_constraints(self.cfg.market.symbol)
        self.store.journal("metadata_loaded", {"symbol": self.cfg.market.symbol})
        self.state.transition(EngineState.RECONCILING)
        rec = reconcile(self.store.load_snapshot(), self.adapter.fetch_open_orders(self.cfg.market.symbol))
        self.store.journal("reconciliation_completed", {"mismatches": rec.mismatch_count})
        if rec.mismatch_count > self.cfg.risk.max_reconciliation_mismatches:
            self.stop("reconciliation mismatch")
            return

        armed = EngineState.ARMED_LIVE if self.cfg.runtime.mode == RuntimeMode.LIVE else EngineState.ARMED_PAPER
        self.state.transition(armed)
        self.state.transition(EngineState.PLACING_INITIAL_GRID)
        market = self.market_data.poll()
        for intent in plan_initial_grid(self.cfg, market, constraints):
            self.order_manager.submit(intent)
        self.state.transition(EngineState.RUNNING)

    def on_private_updates(self) -> None:
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
