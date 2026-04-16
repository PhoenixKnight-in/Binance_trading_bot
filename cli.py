#!/usr/bin/env python3
"""
cli.py — TradingBot CLI entry point.

Usage modes
───────────
  1. One-shot command (argparse subcommands):
       python cli.py place --symbol BTCUSDT --side BUY --type MARKET --qty 0.001
       python cli.py place --symbol ETHUSDT --side SELL --type LIMIT --qty 0.01 --price 3000
       python cli.py cancel --symbol BTCUSDT --order-id 123456
       python cli.py orders [--symbol BTCUSDT]
       python cli.py ping

  2. Interactive menu:
       python cli.py menu

  API credentials are read from environment variables:
       BINANCE_API_KEY
       BINANCE_API_SECRET

  Or pass them explicitly via --api-key / --api-secret.
"""

import argparse
import os
import sys

from bot.client import BinanceClient, BinanceAPIError, BinanceNetworkError
from bot.logging_config import setup_logging, get_logger, LOG_FILE
from bot.orders import place_order, cancel_order, list_open_orders
from dotenv import load_dotenv
load_dotenv()

logger = get_logger("bot.cli")


# ── Credential helpers ────────────────────────────────────────────────────────

def get_credentials(args: argparse.Namespace) -> tuple[str, str]:
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    print("KEY:", api_key[:10])
    print("SECRET:", api_secret[:10])

    if not api_key or not api_secret:
        raise ValueError("BINANCE_API_KEY or BINANCE_API_SECRET not found in environment")

    return api_key.strip(), api_secret.strip()

def build_client(args: argparse.Namespace) -> BinanceClient:
    key, secret = get_credentials(args)
    return BinanceClient(api_key=key, api_secret=secret)


# ── Subcommand handlers ───────────────────────────────────────────────────────

def cmd_ping(args: argparse.Namespace) -> int:
    client = build_client(args)
    ok = client.ping()
    print("Testnet is REACHABLE ✅" if ok else "Testnet is UNREACHABLE ❌")
    return 0 if ok else 1


def cmd_place(args: argparse.Namespace) -> int:
    client = build_client(args)
    try:
        place_order(
            client,
            symbol=args.symbol,
            side=args.side,
            order_type=args.type,
            quantity=args.qty,
            price=getattr(args, "price", None),
            stop_price=getattr(args, "stop_price", None),
            time_in_force=getattr(args, "time_in_force", None),
        )
        return 0
    except (ValueError, BinanceAPIError, BinanceNetworkError) as exc:
        logger.error("place command failed: %s", exc)
        print(f"\nError: {exc}", file=sys.stderr)
        return 1


def cmd_cancel(args: argparse.Namespace) -> int:
    client = build_client(args)
    try:
        cancel_order(client, symbol=args.symbol, order_id=args.order_id)
        return 0
    except (BinanceAPIError, BinanceNetworkError) as exc:
        logger.error("cancel command failed: %s", exc)
        print(f"\nError: {exc}", file=sys.stderr)
        return 1


def cmd_orders(args: argparse.Namespace) -> int:
    client = build_client(args)
    try:
        list_open_orders(client, symbol=getattr(args, "symbol", None))
        return 0
    except (BinanceAPIError, BinanceNetworkError) as exc:
        logger.error("orders command failed: %s", exc)
        print(f"\nError: {exc}", file=sys.stderr)
        return 1


# ── Interactive menu (BONUS) ──────────────────────────────────────────────────

MENU_BANNER = r"""
  ╔══════════════════════════════════════════════╗
  ║     🤖  TRADING BOT — Binance Futures       ║
  ║          Testnet Interactive Menu            ║
  ╚══════════════════════════════════════════════╝
"""

MAIN_MENU = """
  [1] Place MARKET order
  [2] Place LIMIT order
  [3] Place STOP-MARKET order (Bonus)
  [4] Place STOP-LIMIT order  (Bonus)
  [5] List open orders
  [6] Cancel an order
  [7] Ping testnet
  [8] Show log file path
  [0] Exit
"""


def _prompt(label: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"  {label}{suffix}: ").strip()
    return val or (default or "")


def _prompt_optional(label: str) -> str | None:
    val = input(f"  {label} (leave blank to skip): ").strip()
    return val or None


def cmd_menu(args: argparse.Namespace) -> int:
    print(MENU_BANNER)

    # one-time credential setup for the session
    key, secret = get_credentials(args)
    client = BinanceClient(api_key=key, api_secret=secret)

    while True:
        print(MAIN_MENU)
        choice = input("  Select option: ").strip()

        # ── MARKET ────────────────────────────────────────────────────────────
        if choice == "1":
            sym  = _prompt("Symbol (e.g. BTCUSDT)").upper()
            side = _prompt("Side (BUY/SELL)").upper()
            qty  = _prompt("Quantity")
            try:
                place_order(client, symbol=sym, side=side,
                            order_type="MARKET", quantity=qty)
            except Exception as exc:
                print(f"\n  ⚠️  {exc}\n")

        # ── LIMIT ─────────────────────────────────────────────────────────────
        elif choice == "2":
            sym  = _prompt("Symbol (e.g. BTCUSDT)").upper()
            side = _prompt("Side (BUY/SELL)").upper()
            qty  = _prompt("Quantity")
            px   = _prompt("Price")
            tif  = _prompt("TimeInForce", default="GTC")
            try:
                place_order(client, symbol=sym, side=side,
                            order_type="LIMIT", quantity=qty,
                            price=px, time_in_force=tif)
            except Exception as exc:
                print(f"\n  ⚠️  {exc}\n")

        # ── STOP-MARKET (Bonus) ───────────────────────────────────────────────
        elif choice == "3":
            sym   = _prompt("Symbol (e.g. BTCUSDT)").upper()
            side  = _prompt("Side (BUY/SELL)").upper()
            qty   = _prompt("Quantity")
            stop  = _prompt("Stop Price (trigger)")
            try:
                place_order(client, symbol=sym, side=side,
                            order_type="STOP_MARKET", quantity=qty,
                            stop_price=stop)
            except Exception as exc:
                print(f"\n  ⚠️  {exc}\n")

        # ── STOP-LIMIT (Bonus) ────────────────────────────────────────────────
        elif choice == "4":
            sym   = _prompt("Symbol (e.g. BTCUSDT)").upper()
            side  = _prompt("Side (BUY/SELL)").upper()
            qty   = _prompt("Quantity")
            stop  = _prompt("Stop Price (trigger)")
            px    = _prompt("Limit Price")
            tif   = _prompt("TimeInForce", default="GTC")
            try:
                place_order(client, symbol=sym, side=side,
                            order_type="STOP", quantity=qty,
                            price=px, stop_price=stop, time_in_force=tif)
            except Exception as exc:
                print(f"\n  ⚠️  {exc}\n")

        # ── Open orders ───────────────────────────────────────────────────────
        elif choice == "5":
            sym = _prompt_optional("Filter by symbol (e.g. BTCUSDT)")
            try:
                list_open_orders(client, symbol=sym)
            except Exception as exc:
                print(f"\n  ⚠️  {exc}\n")

        # ── Cancel ────────────────────────────────────────────────────────────
        elif choice == "6":
            sym = _prompt("Symbol").upper()
            oid = _prompt("Order ID")
            try:
                cancel_order(client, symbol=sym, order_id=int(oid))
            except Exception as exc:
                print(f"\n  ⚠️  {exc}\n")

        # ── Ping ─────────────────────────────────────────────────────────────
        elif choice == "7":
            ok = client.ping()
            print("  Testnet is REACHABLE ✅" if ok else "  Testnet is UNREACHABLE ❌")

        # ── Log path ─────────────────────────────────────────────────────────
        elif choice == "8":
            print(f"\n  Log file: {LOG_FILE}\n")

        # ── Exit ──────────────────────────────────────────────────────────────
        elif choice == "0":
            print("\n  Goodbye! 👋\n")
            break

        else:
            print("  Invalid option — please choose from the menu.\n")

    return 0


# ── Argument parser ───────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Binance Futures Testnet trading bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Credentials: set BINANCE_API_KEY and BINANCE_API_SECRET env vars,\n"
            "or pass --api-key / --api-secret flags.\n\n"
            "Examples:\n"
            "  python cli.py ping\n"
            "  python cli.py place --symbol BTCUSDT --side BUY --type MARKET --qty 0.001\n"
            "  python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --qty 0.001 --price 50000\n"
            "  python cli.py orders --symbol BTCUSDT\n"
            "  python cli.py cancel --symbol BTCUSDT --order-id 987654\n"
            "  python cli.py menu\n"
        ),
    )

    # ── Global flags ──────────────────────────────────────────────────────────
    parser.add_argument("--api-key",    dest="api_key",    default=None,
                        help="Binance API key (overrides env var)")
    parser.add_argument("--api-secret", dest="api_secret", default=None,
                        help="Binance API secret (overrides env var)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Show DEBUG logs in console")

    sub = parser.add_subparsers(dest="command", required=True)

    # ── ping ──────────────────────────────────────────────────────────────────
    sub.add_parser("ping", help="Check testnet connectivity")

    # ── menu ─────────────────────────────────────────────────────────────────
    sub.add_parser("menu", help="Launch interactive trading menu (Bonus)")

    # ── place ─────────────────────────────────────────────────────────────────
    place_p = sub.add_parser("place", help="Place a new order")
    place_p.add_argument("--symbol",  "-s",  required=True,
                         help="Trading pair, e.g. BTCUSDT")
    place_p.add_argument("--side",           required=True,
                         choices=["BUY", "SELL"],
                         help="Order direction")
    place_p.add_argument("--type",    "-t",  required=True,
                         choices=["MARKET", "LIMIT", "STOP", "STOP_MARKET"],
                         dest="type",
                         help="Order type")
    place_p.add_argument("--qty",     "-q",  required=True,
                         help="Order quantity")
    place_p.add_argument("--price",   "-p",  default=None,
                         help="Limit price (required for LIMIT / STOP)")
    place_p.add_argument("--stop-price",     default=None, dest="stop_price",
                         help="Stop trigger price (required for STOP / STOP_MARKET)")
    place_p.add_argument("--tif",            default="GTC", dest="time_in_force",
                         choices=["GTC", "IOC", "FOK", "GTX"],
                         help="TimeInForce for LIMIT orders (default GTC)")

    # ── cancel ────────────────────────────────────────────────────────────────
    cancel_p = sub.add_parser("cancel", help="Cancel an open order")
    cancel_p.add_argument("--symbol",   "-s", required=True)
    cancel_p.add_argument("--order-id", "-o", required=True, type=int,
                          dest="order_id")

    # ── orders ────────────────────────────────────────────────────────────────
    orders_p = sub.add_parser("orders", help="List open orders")
    orders_p.add_argument("--symbol", "-s", default=None,
                          help="Filter by symbol (optional)")

    return parser


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    setup_logging(verbose=args.verbose)
    logger.debug("CLI started with command: %s", args.command)

    handlers = {
        "ping":   cmd_ping,
        "place":  cmd_place,
        "cancel": cmd_cancel,
        "orders": cmd_orders,
        "menu":   cmd_menu,
    }

    handler = handlers.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    sys.exit(handler(args))


if __name__ == "__main__":
    main()