import hashlib
import hmac
import time
from typing import Any
from urllib.parse import urlencode

import requests

from bot.logging_config import get_logger

logger = get_logger("bot.client")


BASE_URL = "https://testnet.binancefuture.com"
RECV_WINDOW = 5_000          # milliseconds Binance will accept the request within



class BinanceAPIError(Exception):
    """Raised when Binance returns a non-2xx response or an error payload."""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class BinanceNetworkError(Exception):
    """Raised on connectivity / timeout failures."""


# ── Client ────────────────────────────────────────────────────────────────────

class BinanceClient:
    """
    Authenticated Binance USDT-M Futures REST client.

    Args:
        api_key:    Your Testnet API key.
        api_secret: Your Testnet API secret.
        timeout:    HTTP request timeout in seconds (default 10).
    """

    def __init__(self, api_key: str, api_secret: str, timeout: int = 10):
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret must not be empty.")
        self._api_key = api_key
        self._api_secret = api_secret.encode()   # bytes for hmac
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "X-MBX-APIKEY": self._api_key,
            "Content-Type": "application/x-www-form-urlencoded",
        })
        logger.debug("BinanceClient initialised (testnet: %s)", BASE_URL)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _sign(self, params: dict) -> str:
        """Return HMAC-SHA256 hex signature of the query string."""
        query = urlencode(params)
        sig = hmac.new(self._api_secret, query.encode(), hashlib.sha256).hexdigest()  # type: ignore[attr-defined]
        return sig

    def _timestamp(self) -> int:
        return int(time.time() * 1000)

    def _request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        signed: bool = True,
    ) -> Any:
        
        params = params or {}

        if signed:
            params["timestamp"] = self._timestamp()
            params["recvWindow"] = RECV_WINDOW
            params["signature"] = self._sign(params)

        url = BASE_URL + path

        logger.debug("→ %s %s | params=%s", method, path, {
            k: v for k, v in params.items() if k != "signature"
        })

        try:
            if method == "GET":
                resp = self._session.get(url, params=params, timeout=self._timeout)
            elif method == "POST":
                resp = self._session.post(url, data=params, timeout=self._timeout)
            elif method == "DELETE":
                resp = self._session.delete(url, params=params, timeout=self._timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
        except requests.exceptions.Timeout as exc:
            logger.error("Request timed out: %s %s", method, path)
            raise BinanceNetworkError(f"Request timed out ({self._timeout}s)") from exc
        except requests.exceptions.ConnectionError as exc:
            logger.error("Connection error: %s", exc)
            raise BinanceNetworkError(f"Connection failed: {exc}") from exc

        logger.debug("← %s %s | status=%d | body=%s",
                     method, path, resp.status_code,
                     resp.text[:400])   # truncate huge responses in logs

        # ── Parse JSON ────────────────────────────────────────────────────────
        try:
            data = resp.json()
        except ValueError:
            logger.error("Non-JSON response: %s", resp.text[:200])
            raise BinanceAPIError(-1, f"Non-JSON response: {resp.text[:200]}")

        # ── Detect Binance error payload ───────────────────────────────────────
        if isinstance(data, dict) and "code" in data and data["code"] != 200:
            logger.error("Binance API error %s: %s", data["code"], data.get("msg"))
            raise BinanceAPIError(data["code"], data.get("msg", "Unknown error"))

        if not resp.ok:
            logger.error("HTTP %d: %s", resp.status_code, resp.text[:200])
            raise BinanceAPIError(resp.status_code, resp.text[:200])

        return data

    # ── Public API ────────────────────────────────────────────────────────────

    def ping(self) -> bool:
        """Return True if the testnet is reachable."""
        try:
            self._request("GET", "/fapi/v1/ping", signed=False)
            logger.info("Ping successful — testnet is reachable.")
            return True
        except (BinanceAPIError, BinanceNetworkError) as exc:
            logger.warning("Ping failed: %s", exc)
            return False

    def get_server_time(self) -> int:
        """Return Binance server time (ms)."""
        data = self._request("GET", "/fapi/v1/time", signed=False)
        return data["serverTime"]

    def get_account_info(self) -> dict:
        """Return futures account information."""
        return self._request("GET", "/fapi/v2/account")

    def get_exchange_info(self) -> dict:
        """Return exchange trading rules and symbol info."""
        return self._request("GET", "/fapi/v1/exchangeInfo", signed=False)

    def get_symbol_info(self, symbol: str) -> dict | None:
        """Return rules for a specific symbol, or None if not found."""
        info = self.get_exchange_info()
        for s in info.get("symbols", []):
            if s["symbol"] == symbol.upper():
                return s
        return None

    def place_order(self, **params) -> dict:
        """
        Place an order on USDT-M Futures.

        Keyword args are passed directly to POST /fapi/v1/order.
        Required fields depend on order type (handled by orders.py).
        """
        logger.info("Placing order: %s", {k: v for k, v in params.items()})
        result = self._request("POST", "/fapi/v1/order", params=dict(params))
        logger.info("Order response: orderId=%s status=%s",
                    result.get("orderId"), result.get("status"))
        return result

    def cancel_order(self, symbol: str, order_id: int) -> dict:
        """Cancel an open order by orderId."""
        params = {"symbol": symbol.upper(), "orderId": order_id}
        logger.info("Cancelling order %s on %s", order_id, symbol)
        return self._request("DELETE", "/fapi/v1/order", params=params)

    def get_open_orders(self, symbol: str | None = None) -> list:
        """Return all open orders, optionally filtered by symbol."""
        params = {}
        if symbol:
            params["symbol"] = symbol.upper()
        return self._request("GET", "/fapi/v1/openOrders", params=params)

    def get_order(self, symbol: str, order_id: int) -> dict:
        """Fetch a single order by orderId."""
        params = {"symbol": symbol.upper(), "orderId": order_id}
        return self._request("GET", "/fapi/v1/order", params=params)