from __future__ import annotations

from domain.enums import RiskStopReason


def check_inventory(max_inventory, inventory_qty):
    if inventory_qty > max_inventory:
        return RiskStopReason.MAX_INVENTORY
    return None
