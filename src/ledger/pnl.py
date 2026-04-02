from domain.models import PnLSnapshot


class PnLLedger:
    def __init__(self, snapshot: PnLSnapshot) -> None:
        self.snapshot = snapshot

    def apply_trade(self, realized_quote, fee_quote) -> None:
        self.snapshot.realized_quote += realized_quote
        self.snapshot.fees_quote += fee_quote
