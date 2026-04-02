from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from domain.models import BalanceSnapshot, InventorySnapshot, OpenOrder, PersistedSnapshot, PnLSnapshot


class SQLiteStore:
    def __init__(self, path: str) -> None:
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self.conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS journal (id INTEGER PRIMARY KEY, event_type TEXT NOT NULL, payload TEXT NOT NULL)")
        cur.execute("CREATE TABLE IF NOT EXISTS snapshots (id INTEGER PRIMARY KEY, state TEXT NOT NULL, payload TEXT NOT NULL)")
        self.conn.commit()

    def journal(self, event_type: str, payload: dict) -> None:
        self.conn.execute("INSERT INTO journal(event_type, payload) VALUES(?, ?)", (event_type, json.dumps(payload)))
        self.conn.commit()

    def write_snapshot(self, snapshot: PersistedSnapshot) -> None:
        payload = {
            "balances": snapshot.balances.__dict__,
            "inventory": snapshot.inventory.__dict__,
            "pnl": snapshot.pnl.__dict__,
            "open_orders": [o.__dict__ for o in snapshot.open_orders],
            "ts": snapshot.ts.isoformat(),
        }
        self.conn.execute("INSERT INTO snapshots(state, payload) VALUES(?, ?)", (snapshot.state, json.dumps(payload, default=str)))
        self.conn.commit()

    def load_snapshot(self) -> PersistedSnapshot | None:
        row = self.conn.execute("SELECT state, payload FROM snapshots ORDER BY id DESC LIMIT 1").fetchone()
        if not row:
            return None
        state, payload_raw = row
        payload = json.loads(payload_raw)
        orders = [OpenOrder(**o) for o in payload["open_orders"]]
        return PersistedSnapshot(
            state=state,
            balances=BalanceSnapshot(**payload["balances"]),
            inventory=InventorySnapshot(**payload["inventory"]),
            pnl=PnLSnapshot(**payload["pnl"]),
            open_orders=orders,
        )
