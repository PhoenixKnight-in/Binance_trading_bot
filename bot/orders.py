"""
Order placement logic — sits between CLI and the raw HTTP client.

Responsibilities
────────────────
* Convert validated Python values to Binance API parameters.
* Pretty-print order request summaries and responses.
* Return structured results to the CLI layer.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from bot.client import BinanceClient, BinanceAPIError, BinanceNetworkError
from bot.logging_config import get_logger
from bot.validators import validate_order_params

logger = get_logger("bot.orders")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt(value: Optional[str | float | Decimal], decimals: int = 8) -> str:
    """Format a numeric string/Decimal for display; return '-' if None/empty."""
    if value is None or value == "" or value == "0":
        return "-"
    try:
        return f"{Decimal(str(value)):.{decimals}f}"
    except Exception:
        return str(value)


def _print_separator(char: str = "─", width: int = 60) -> None:
    print(char * width)


def _print_request_summary(params: dict) -> None:
    """Print a human-readable summary of what is about to be placed."""
    _print_separator()
    print("  📋  ORDER REQUEST SUMMARY")
    _print_separator()
    print(f"  Symbol      : {params['symbol']}")
    print(f"  Side        : {params['side']}")
    print(f"  Type        : {params['type']}")
    print(f"  Quantity    : {params['quantity']}")
    if "price" in params:
        print(f"  Price       : {params['price']}")
    if "stopPrice" in params:
        print(f"  Stop Price  : {params['stopPrice']}")
    if "timeInForce" in params:
        print(f"  TimeInForce : {params['timeInForce']}")
    _print_separator()


def _print_order_response(resp: dict) -> None:
    """Print key fields from the Binance order response."""
    print()
    _print_separator()
    print("  ✅  ORDER PLACED SUCCESSFULLY")
    _print_separator()
    print(f"  Order ID    : {resp.get('orderId', '-')}")
    print(f"  Client OID  : {resp.get('clientOrderId', '-')}")
    print(f"  Symbol      : {resp.get('symbol', '-')}")
    print(f"  Side        : {resp.get('side', '-')}")
    print(f"  Type        : {resp.get('type', '-')}")
    print(f"  Status      : {resp.get('status', '-')}")
    print(f"  Qty (orig)  : {_fmt(resp.get('origQty'))}")
    print(f"  Qty (exec)  : {_fmt(resp.get('executedQty'))}")

    avg_price = resp.get("avgPrice") or resp.get("price")
    print(f"  Avg Price   : {_fmt(avg_price)}")

    if resp.get("stopPrice") and resp["stopPrice"] != "0":
        print(f"  Stop Price  : {_fmt(resp['stopPrice'])}")

    print(f"  Time (ms)   : {resp.get('updateTime', '-')}")
    _print_separator()
    print()


# ── Core order functions ──────────────────────────────────────────────────────

def place_order(
    client: BinanceClient,
    *,
    symbol: str,
    side: str,
    order_type: str,
    quantity: str | float,
    price: Optional[str | float] = None,
    stop_price: Optional[str | float] = None,
    time_in_force: Optional[str] = None,
) -> dict:
    """
    Validate, log, and place a single order.

    Args:
        client:        Authenticated BinanceClient instance.
        symbol:        e.g. "BTCUSDT"
        side:          "BUY" or "SELL"
        order_type:    "MARKET", "LIMIT", "STOP", or "STOP_MARKET"
        quantity:      Order quantity.
        price:         Limit price (required for LIMIT / STOP).
        stop_price:    Stop trigger price (required for STOP / STOP_MARKET).
        time_in_force: "GTC" | "IOC" | "FOK" | "GTX" (default GTC for LIMIT).

    Returns:
        Raw Binance response dict.

    Raises:
        ValueError:          On invalid input.
        BinanceAPIError:     On Binance error responses.
        BinanceNetworkError: On network failures.
    """
    logger.info(
        "Order requested — symbol=%s side=%s type=%s qty=%s price=%s",
        symbol, side, order_type, quantity, price,
    )

    # ── Validate ──────────────────────────────────────────────────────────────
    params = validate_order_params(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price,
        stop_price=stop_price,
        time_in_force=time_in_force,
    )

    _print_request_summary(params)

    # ── Convert Decimals → strings for the API ────────────────────────────────
    api_params: dict = {}
    for key, val in params.items():
        api_params[key] = str(val) if isinstance(val, Decimal) else val

    # ── Send to exchange ──────────────────────────────────────────────────────
    try:
        response = client.place_order(**api_params)
    except BinanceAPIError as exc:
        logger.error("Order failed — Binance API error: %s", exc)
        print(f"\n  ❌  ORDER FAILED")
        print(f"  Binance error [{exc.code}]: {exc.message}\n")
        raise
    except BinanceNetworkError as exc:
        logger.error("Order failed — network error: %s", exc)
        print(f"\n  ❌  NETWORK ERROR: {exc}\n")
        raise

    _print_order_response(response)
    return response


def cancel_order(
    client: BinanceClient,
    symbol: str,
    order_id: int,
) -> dict:
    """Cancel an open order and print the result."""
    logger.info("Cancel requested — symbol=%s orderId=%s", symbol, order_id)
    try:
        resp = client.cancel_order(symbol, order_id)
        _print_separator()
        print(f"  🚫  ORDER CANCELLED  — orderId={resp.get('orderId')}  status={resp.get('status')}")
        _print_separator()
        return resp
    except (BinanceAPIError, BinanceNetworkError) as exc:
        logger.error("Cancel failed: %s", exc)
        print(f"\n  ❌  CANCEL FAILED: {exc}\n")
        raise


def list_open_orders(
    client: BinanceClient,
    symbol: Optional[str] = None,
) -> list:
    """Fetch and display open orders."""
    orders = client.get_open_orders(symbol)
    if not orders:
        print("  ℹ️   No open orders found.")
        return []

    _print_separator()
    print(f"  📂  OPEN ORDERS ({len(orders)})")
    _print_separator()
    for o in orders:
        avg = _fmt(o.get("avgPrice") or o.get("price"))
        print(
            f"  [{o['orderId']}] {o['symbol']} {o['side']} {o['type']} "
            f"qty={_fmt(o.get('origQty'))} price={avg} status={o['status']}"
        )
    _print_separator()
    return orders