from __future__ import annotations

from domain.enums import EngineState
from domain.errors import ValidationError


class EngineStateMachine:
    def __init__(self) -> None:
        self.state = EngineState.BOOTSTRAP

    def transition(self, next_state: EngineState) -> None:
        allowed: dict[EngineState, set[EngineState]] = {
            EngineState.BOOTSTRAP: {EngineState.VALIDATING_CONFIG},
            EngineState.VALIDATING_CONFIG: {EngineState.LOADING_METADATA, EngineState.ERROR, EngineState.STOPPING},
            EngineState.LOADING_METADATA: {EngineState.RECONCILING, EngineState.ERROR, EngineState.STOPPING},
            EngineState.RECONCILING: {EngineState.ARMED_PAPER, EngineState.ARMED_LIVE, EngineState.ERROR, EngineState.STOPPING},
            EngineState.ARMED_PAPER: {EngineState.PLACING_INITIAL_GRID, EngineState.STOPPING},
            EngineState.ARMED_LIVE: {EngineState.PLACING_INITIAL_GRID, EngineState.STOPPING},
            EngineState.PLACING_INITIAL_GRID: {EngineState.RUNNING, EngineState.ERROR, EngineState.STOPPING},
            EngineState.RUNNING: {EngineState.PAUSED_RISK, EngineState.STOPPING, EngineState.ERROR},
            EngineState.PAUSED_RISK: {EngineState.STOPPING, EngineState.RUNNING},
            EngineState.ERROR: {EngineState.STOPPING},
            EngineState.STOPPING: {EngineState.STOPPED},
            EngineState.STOPPED: set(),
        }
        if next_state not in allowed.get(self.state, set()):
            raise ValidationError(f"invalid state transition {self.state} -> {next_state}")
        self.state = next_state
