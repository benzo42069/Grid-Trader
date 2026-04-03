from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import threading
import time
from datetime import datetime, timezone
from decimal import Decimal
from queue import Empty, Queue
from typing import Any
from urllib.parse import urlencode

import requests
import websocket

from domain.enums import OrderStatus, Side
from domain.errors import ExchangeError, ValidationError
from domain.models import BalanceSnapshot, CancelResult, FillEvent, MarketSnapshot, OpenOrder, OrderIntent, SymbolConstraints
from exchange.base import SpotExchangeAdapter
from exchange.constraints import normalize_price_qty
from exchange.types import HealthStatus

LOGGER = logging.getLogger(__name__)


class KrakenSpotAdapter(SpotExchangeAdapter):
    REST_BASE = "https://api.kraken.com"
    PUBLIC_WS_URL = "wss://ws.kraken.com/v2"
    PRIVATE_WS_URL = "wss://ws-auth.kraken.com/v2"

    def __init__(self, api_key: str, api_secret: str, *, timeout_seconds: int = 10) -> None:
        if not api_key or not api_secret:
            raise ValidationError("kraken credentials are required")
        self._api_key = api_key
        self._api_secret = api_secret
        self._session = requests.Session()
        self._timeout = timeout_seconds
        self._nonce = int(time.time() * 1000)
        self._constraints_cache: dict[str, SymbolConstraints] = {}
        self._rest_pair_by_symbol: dict[str, str] = {}
        self._ws_symbol_by_symbol: dict[str, str] = {}
        self._symbol_by_ws_symbol: dict[str, str] = {}

        self._last_market_ts: float = 0.0
        self._last_private_ts: float = 0.0
        self._ticker_by_symbol: dict[str, MarketSnapshot] = {}
        self._fills_queue: Queue[FillEvent] = Queue()

        self._public_ws: websocket.WebSocketApp | None = None
        self._private_ws: websocket.WebSocketApp | None = None

    def load_symbol_constraints(self, symbol: str) -> SymbolConstraints:
        if symbol in self._constraints_cache:
            return self._constraints_cache[symbol]

        payload = self._public_request("/0/public/AssetPairs", {})
        for pair_name, row in payload.items():
            wsname = row.get("wsname")
            if not wsname:
                continue
            if wsname.upper() != symbol.upper():
                continue
            tick_scale = int(row.get("pair_decimals", 5))
            step_scale = int(row.get("lot_decimals", 8))
            constraints = SymbolConstraints(
                symbol=symbol,
                tick_size=Decimal("1").scaleb(-tick_scale),
                step_size=Decimal("1").scaleb(-step_scale),
                min_qty=Decimal(row.get("ordermin", "0.00000001")),
                min_notional=Decimal("5"),
                supports_post_only=True,
            )
            self._constraints_cache[symbol] = constraints
            self._rest_pair_by_symbol[symbol] = pair_name
            self._ws_symbol_by_symbol[symbol] = wsname
            self._symbol_by_ws_symbol[wsname] = symbol
            self._ensure_public_ws(symbol)
            self._ensure_private_ws()
            return constraints

        raise ValidationError(f"kraken does not support symbol {symbol}")

    def fetch_balances(self, symbol: str) -> BalanceSnapshot:
        base, quote = symbol.split("/", 1)
        payload = self._private_request("/0/private/Balance", {})
        quote_free = self._extract_balance(payload, quote)
        base_free = self._extract_balance(payload, base)
        return BalanceSnapshot(free_quote=quote_free, locked_quote=Decimal("0"), free_base=base_free, locked_base=Decimal("0"))

    def fetch_open_orders(self, symbol: str) -> list[OpenOrder]:
        pair_code = self._rest_pair(symbol)
        payload = self._private_request("/0/private/OpenOrders", {})
        open_map = payload.get("open", {})
        orders: list[OpenOrder] = []
        for order_id, details in open_map.items():
            descr = details.get("descr", {})
            if descr.get("pair") not in {pair_code, self._ws_symbol_by_symbol.get(symbol), symbol.replace("/", "")}:
                continue
            client_order_id = str(details.get("cl_ord_id") or details.get("userref") or order_id)
            side = Side.BUY if descr.get("type") == "buy" else Side.SELL
            orders.append(
                OpenOrder(
                    symbol=symbol,
                    exchange_order_id=order_id,
                    client_order_id=client_order_id,
                    side=side,
                    price=Decimal(descr.get("price", "0")),
                    quantity=Decimal(descr.get("order", "0 0").split(" ")[-1]),
                    filled_qty=Decimal(details.get("vol_exec", "0")),
                    status=OrderStatus.OPEN,
                )
            )
        return orders

    def fetch_recent_fills(self, symbol: str) -> list[FillEvent]:
        # Primary source is private websocket. REST fallback kept empty to avoid duplicate fill processing.
        return []

    def place_managed_order_intent(self, intent: OrderIntent) -> OpenOrder:
        constraints = self.load_symbol_constraints(intent.symbol)
        price, qty = normalize_price_qty(intent.price, intent.quantity, constraints)
        payload: dict[str, str] = {
            "pair": self._rest_pair(intent.symbol),
            "type": intent.side.value,
            "ordertype": "limit",
            "price": format(price, "f"),
            "volume": format(qty, "f"),
            "timeinforce": "GTC",
            "cl_ord_id": intent.client_order_id,
            "userref": str(self._userref(intent.client_order_id)),
        }
        if intent.post_only:
            payload["oflags"] = "post"

        result = self._private_request("/0/private/AddOrder", payload)
        txids = result.get("txid") or []
        if not txids:
            raise ExchangeError("kraken did not return order txid")
        return OpenOrder(
            symbol=intent.symbol,
            exchange_order_id=str(txids[0]),
            client_order_id=intent.client_order_id,
            side=intent.side,
            price=price,
            quantity=qty,
            status=OrderStatus.OPEN,
        )

    def cancel_managed_order(self, symbol: str, client_order_id: str) -> CancelResult:
        payload = {"cl_ord_id": client_order_id}
        try:
            result = self._private_request("/0/private/CancelOrder", payload)
            canceled_count = int(result.get("count", 0))
            return CancelResult(client_order_id=client_order_id, canceled=canceled_count > 0)
        except ExchangeError as exc:
            return CancelResult(client_order_id=client_order_id, canceled=False, reason=str(exc))

    def cancel_all_managed_orders(self, symbol: str) -> list[CancelResult]:
        orders = self.fetch_open_orders(symbol)
        return [self.cancel_managed_order(symbol, o.client_order_id) for o in orders]

    def read_market_data(self, symbol: str) -> MarketSnapshot:
        self.load_symbol_constraints(symbol)
        snap = self._ticker_by_symbol.get(symbol)
        if snap is not None:
            return snap

        ticker = self._public_request("/0/public/Ticker", {"pair": self._rest_pair(symbol)})
        row = next(iter(ticker.values()))
        return MarketSnapshot(symbol=symbol, bid=Decimal(row["b"][0]), ask=Decimal(row["a"][0]))

    def read_private_updates(self, symbol: str) -> list[FillEvent]:
        fills: list[FillEvent] = []
        while True:
            try:
                fill = self._fills_queue.get_nowait()
                if fill.symbol == symbol:
                    fills.append(fill)
            except Empty:
                return fills

    def health_check(self) -> HealthStatus:
        now = time.time()
        market_ok = now - self._last_market_ts < 30 if self._last_market_ts else False
        private_ok = now - self._last_private_ts < 30 if self._last_private_ts else False
        return HealthStatus(market_data_ok=market_ok, private_stream_ok=private_ok)

    def _extract_balance(self, payload: dict[str, Any], code: str) -> Decimal:
        aliases = [code.upper(), f"X{code.upper()}", f"Z{code.upper()}"]
        if code.upper() == "USD":
            aliases.append("ZUSD")
        if code.upper() == "DOGE":
            aliases.extend(["XDG", "XXDG"])
        for alias in aliases:
            if alias in payload:
                return Decimal(str(payload[alias]))
        return Decimal("0")

    def _rest_pair(self, symbol: str) -> str:
        if symbol not in self._rest_pair_by_symbol:
            self.load_symbol_constraints(symbol)
        return self._rest_pair_by_symbol[symbol]

    def _public_request(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        response = self._session.get(f"{self.REST_BASE}{path}", params=params, timeout=self._timeout)
        return self._parse_response(response)

    def _private_request(self, path: str, payload: dict[str, str]) -> dict[str, Any]:
        nonce = self._next_nonce()
        encoded = {**payload, "nonce": str(nonce)}
        postdata = urlencode(encoded)
        sha256 = hashlib.sha256((str(nonce) + postdata).encode()).digest()
        message = path.encode() + sha256
        secret = base64.b64decode(self._api_secret)
        signature = base64.b64encode(hmac.new(secret, message, hashlib.sha512).digest()).decode()
        headers = {"API-Key": self._api_key, "API-Sign": signature}
        response = self._session.post(f"{self.REST_BASE}{path}", data=encoded, headers=headers, timeout=self._timeout)
        return self._parse_response(response)

    def _parse_response(self, response: requests.Response) -> dict[str, Any]:
        try:
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:  # noqa: BLE001
            raise ExchangeError(f"kraken request failed: {exc}") from exc
        errors = payload.get("error") or []
        if errors:
            raise ExchangeError(f"kraken error: {'; '.join(errors)}")
        result = payload.get("result")
        if not isinstance(result, dict):
            raise ExchangeError("kraken response missing result payload")
        return result

    def _next_nonce(self) -> int:
        self._nonce += 1
        return self._nonce

    def _ensure_public_ws(self, symbol: str) -> None:
        if self._public_ws is not None:
            return

        def on_message(_ws, message: str) -> None:
            try:
                payload = json.loads(message)
            except json.JSONDecodeError:
                return
            if payload.get("channel") != "ticker" or payload.get("type") != "update":
                return
            data = payload.get("data") or []
            for row in data:
                ws_symbol = row.get("symbol")
                canonical_symbol = self._symbol_by_ws_symbol.get(ws_symbol)
                if not canonical_symbol:
                    continue
                bid = row.get("bid")
                ask = row.get("ask")
                if bid is None or ask is None:
                    continue
                self._ticker_by_symbol[canonical_symbol] = MarketSnapshot(
                    symbol=canonical_symbol,
                    bid=Decimal(str(bid)),
                    ask=Decimal(str(ask)),
                    ts=datetime.now(timezone.utc),
                )
                self._last_market_ts = time.time()

        def on_open(ws) -> None:
            subscription = {
                "method": "subscribe",
                "params": {
                    "channel": "ticker",
                    "symbol": [self._ws_symbol_by_symbol[symbol]],
                    "snapshot": False,
                },
            }
            ws.send(json.dumps(subscription))

        self._public_ws = websocket.WebSocketApp(self.PUBLIC_WS_URL, on_open=on_open, on_message=on_message)
        threading.Thread(target=self._public_ws.run_forever, kwargs={"ping_interval": 15, "ping_timeout": 10}, daemon=True).start()

    def _ensure_private_ws(self) -> None:
        if self._private_ws is not None:
            return
        token_payload = self._private_request("/0/private/GetWebSocketsToken", {})
        token = token_payload["token"]

        def on_message(_ws, message: str) -> None:
            try:
                payload = json.loads(message)
            except json.JSONDecodeError:
                return
            if payload.get("channel") != "executions" or payload.get("type") != "update":
                return
            rows = payload.get("data") or []
            for row in rows:
                if row.get("exec_type") not in {"trade", "filled"}:
                    continue
                ws_symbol = row.get("symbol")
                canonical_symbol = self._symbol_by_ws_symbol.get(ws_symbol, ws_symbol)
                fill = FillEvent(
                    fill_id=str(row.get("exec_id") or row.get("trade_id") or row.get("order_id")),
                    symbol=canonical_symbol,
                    client_order_id=str(row.get("cl_ord_id") or row.get("userref") or row.get("order_id")),
                    side=Side.BUY if row.get("side") == "buy" else Side.SELL,
                    price=Decimal(str(row.get("last_price") or row.get("limit_price") or "0")),
                    quantity=Decimal(str(row.get("last_qty") or row.get("last_quantity") or "0")),
                    fee_quote=Decimal(str(row.get("fee") or "0")),
                    ts=datetime.now(timezone.utc),
                )
                self._fills_queue.put(fill)
                self._last_private_ts = time.time()

        def on_open(ws) -> None:
            ws.send(
                json.dumps(
                    {
                        "method": "subscribe",
                        "params": {
                            "channel": "executions",
                            "token": token,
                            "snapshot": False,
                        },
                    }
                )
            )

        self._private_ws = websocket.WebSocketApp(self.PRIVATE_WS_URL, on_open=on_open, on_message=on_message)
        threading.Thread(target=self._private_ws.run_forever, kwargs={"ping_interval": 15, "ping_timeout": 10}, daemon=True).start()

    @staticmethod
    def _userref(client_order_id: str) -> int:
        digest = hashlib.sha256(client_order_id.encode("utf-8")).hexdigest()
        return int(digest[:8], 16)
