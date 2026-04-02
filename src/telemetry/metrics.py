class NullMetrics:
    def incr(self, name: str, value: int = 1) -> None:
        _ = (name, value)
