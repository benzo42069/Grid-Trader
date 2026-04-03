from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from decimal import Decimal
from enum import Enum
from pathlib import Path
from sqlite3 import Error as SQLiteError

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

    def is_healthy(self) -> bool:
        try:
            self.conn.execute("SELECT 1")
            return True
        except SQLiteError:
            return False

    def journal(self, event_type: str, payload: dict) -> None:
        self.conn.execute("INSERT INTO journal(event_type, payload) VALUES(?, ?)", (event_type, json.dumps(payload)))
        self.conn.commit()

    def _json_ready(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, dict):
            return {k: self._json_ready(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._json_ready(v) for v in obj]
        return obj

    def write_snapshot(self, snapshot: PersistedSnapshot) -> None:
        payload = {
            "balances": asdict(snapshot.balances),
            "inventory": asdict(snapshot.inventory),
            "pnl": asdict(snapshot.pnl),
            "open_orders": [asdict(o) for o in snapshot.open_orders],
            "config_hash": snapshot.config_hash,
            "ts": snapshot.ts.isoformat(),
        }
        self.conn.execute("INSERT INTO snapshots(state, payload) VALUES(?, ?)", (snapshot.state, json.dumps(self._json_ready(payload))))
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
            balances=BalanceSnapshot(**{k: Decimal(v) for k, v in payload["balances"].items()}),
            inventory=InventorySnapshot(**{k: Decimal(v) for k, v in payload["inventory"].items()}),
            pnl=PnLSnapshot(**{k: Decimal(v) for k, v in payload["pnl"].items()}),
            open_orders=orders,
            config_hash=payload.get("config_hash", ""),
        )
