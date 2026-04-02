from domain.models import PersistedSnapshot


def build_snapshot(state: str, balances, inventory, pnl, open_orders):
    return PersistedSnapshot(state=state, balances=balances, inventory=inventory, pnl=pnl, open_orders=open_orders)
