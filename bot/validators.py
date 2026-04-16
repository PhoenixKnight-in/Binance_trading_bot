"""
Input validation for trading parameters.

All validators raise ValueError with a human-readable message on failure
and return the cleaned / normalised value on success.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional

# ── Constants ─────────────────────────────────────────────────────────────────

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET", "STOP"}   # base + bonus
VALID_TIME_IN_FORCE = {"GTC", "IOC", "FOK", "GTX"}


# ── Individual validators ─────────────────────────────────────────────────────

def validate_symbol(symbol: str) -> str:
    """
    Ensure symbol is a non-empty uppercase alphabetic string.

    Raises:
        ValueError: If the symbol is blank or contains invalid characters.
    """
    s = symbol.strip().upper()
    if not s:
        raise ValueError("Symbol must not be empty.")
    if not s.isalpha():
        raise ValueError(
            f"Symbol '{s}' contains invalid characters. "
            "Expected uppercase letters only (e.g. BTCUSDT)."
        )
    return s


def validate_side(side: str) -> str:
    """Return 'BUY' or 'SELL'; raise ValueError otherwise."""
    s = side.strip().upper()
    if s not in VALID_SIDES:
        raise ValueError(
            f"Side '{side}' is invalid. Choose from: {', '.join(sorted(VALID_SIDES))}."
        )
    return s


def validate_order_type(order_type: str) -> str:
    """Return a valid order type string; raise ValueError otherwise."""
    t = order_type.strip().upper()
    if t not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Order type '{order_type}' is not supported. "
            f"Choose from: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return t


def validate_quantity(quantity: str | float | Decimal) -> Decimal:
    """
    Parse and validate order quantity.

    Rules:
        * Must be a positive number.
        * Must not be zero.

    Returns:
        Decimal representation.
    """
    try:
        qty = Decimal(str(quantity))
    except InvalidOperation:
        raise ValueError(f"Quantity '{quantity}' is not a valid number.")
    if qty <= 0:
        raise ValueError(f"Quantity must be greater than zero, got {qty}.")
    return qty


def validate_price(
    price: Optional[str | float | Decimal],
    *,
    required: bool = False,
) -> Optional[Decimal]:
    """
    Parse and validate order price.

    Args:
        price:    Raw price value (may be None for MARKET orders).
        required: If True, raise when price is None or zero.

    Returns:
        Decimal price, or None if price is not applicable.
    """
    if price is None or price == "":
        if required:
            raise ValueError("Price is required for this order type.")
        return None

    try:
        p = Decimal(str(price))
    except InvalidOperation:
        raise ValueError(f"Price '{price}' is not a valid number.")
    if p <= 0:
        raise ValueError(f"Price must be greater than zero, got {p}.")
    return p


def validate_stop_price(
    stop_price: Optional[str | float | Decimal],
    *,
    required: bool = False,
) -> Optional[Decimal]:
    """Same rules as price but labelled 'stop price' in error messages."""
    if stop_price is None or stop_price == "":
        if required:
            raise ValueError("Stop price is required for Stop-Limit orders.")
        return None
    try:
        sp = Decimal(str(stop_price))
    except InvalidOperation:
        raise ValueError(f"Stop price '{stop_price}' is not a valid number.")
    if sp <= 0:
        raise ValueError(f"Stop price must be greater than zero, got {sp}.")
    return sp


def validate_time_in_force(tif: Optional[str]) -> str:
    """Return a valid TimeInForce value (default GTC)."""
    if not tif:
        return "GTC"
    t = tif.strip().upper()
    if t not in VALID_TIME_IN_FORCE:
        raise ValueError(
            f"timeInForce '{tif}' is invalid. "
            f"Choose from: {', '.join(sorted(VALID_TIME_IN_FORCE))}."
        )
    return t


# ── Composite validator ───────────────────────────────────────────────────────

def validate_order_params(
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
    Validate all order parameters at once.

    Returns a dict of cleaned values ready for the API layer.

    Raises:
        ValueError: With a descriptive message for the first validation failure.
    """
    cleaned = {
        "symbol": validate_symbol(symbol),
        "side": validate_side(side),
        "type": validate_order_type(order_type),
        "quantity": validate_quantity(quantity),
    }

    ot = cleaned["type"]

    # LIMIT and STOP require price
    if ot in ("LIMIT", "STOP"):
        cleaned["price"] = validate_price(price, required=True)
        cleaned["timeInForce"] = validate_time_in_force(time_in_force)

    # STOP / STOP_MARKET require stopPrice
    if ot in ("STOP", "STOP_MARKET"):
        cleaned["stopPrice"] = validate_stop_price(stop_price, required=True)

    # MARKET — price is irrelevant
    if ot == "MARKET" and price:
        raise ValueError("Price must not be set for MARKET orders.")

    return cleaned