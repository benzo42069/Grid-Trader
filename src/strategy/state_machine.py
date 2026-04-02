from __future__ import annotations

from domain.enums import EngineState
from domain.errors import ValidationError


class EngineStateMachine:
    def __init__(self) -> None:
        self.state = EngineState.BOOTSTRAP

    def transition(self, next_state: EngineState) -> None:
        if self.state == EngineState.STOPPED:
            raise ValidationError("cannot transition from STOPPED")
        self.state = next_state
