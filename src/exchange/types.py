from dataclasses import dataclass


@dataclass(slots=True)
class HealthStatus:
    market_data_ok: bool
    private_stream_ok: bool
