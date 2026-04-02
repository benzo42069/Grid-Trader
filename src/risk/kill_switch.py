from domain.enums import RiskStopReason


class KillSwitch:
    def __init__(self) -> None:
        self.reason: RiskStopReason | None = None

    def trigger(self, reason: RiskStopReason) -> None:
        self.reason = reason

    @property
    def active(self) -> bool:
        return self.reason is not None
