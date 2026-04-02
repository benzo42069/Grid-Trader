class EngineError(Exception):
    """Base engine error."""


class ConfigError(EngineError):
    pass


class ValidationError(EngineError):
    pass


class ExchangeError(EngineError):
    pass


class RetryableExchangeError(ExchangeError):
    pass


class FatalExchangeError(ExchangeError):
    pass


class AmbiguousExchangeError(ExchangeError):
    pass


class ReconciliationError(EngineError):
    pass


class PersistenceError(EngineError):
    pass


class RiskStopError(EngineError):
    pass
