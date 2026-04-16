# 🤖 TradingBot — Binance Futures Testnet

A clean, production-structured Python CLI application for placing orders on **Binance USDT-M Futures Testnet**.

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py          # Package marker
│   ├── client.py            # BinanceClient — auth, signing, HTTP
│   ├── orders.py            # Order placement logic + display
│   ├── validators.py        # Input validation (symbol, side, qty, price…)
│   └── logging_config.py    # Rotating file + console logging setup
├── cli.py                   # CLI entry point (argparse subcommands + interactive menu)
├── logs/
│   └── trading_bot.log      # Auto-created; rotates at 5 MB (keeps 5 backups)
├── README.md
└── requirements.txt
```

---

## Setup

### 1. Prerequisites

- Python 3.10 or later
- A Binance Futures Testnet account

### 2. Get Testnet Credentials

1. Go to https://testnet.binancefuture.com
2. Log in (GitHub OAuth or email)
3. Navigate to **API Key** → **Generate**
4. Copy your **API Key** and **Secret Key**

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Credentials

**Recommended — environment variables:**

```bash
# Linux / macOS
export BINANCE_API_KEY="your_api_key_here"
export BINANCE_API_SECRET="your_secret_here"

# Windows PowerShell
$env:BINANCE_API_KEY="your_api_key_here"
$env:BINANCE_API_SECRET="your_secret_here"
```

**Alternative — CLI flags** (any subcommand accepts these):

```bash
python cli.py --api-key YOUR_KEY --api-secret YOUR_SECRET place ...
```

**Alternative — interactive prompt:**  
If credentials are not found anywhere, the app will prompt you securely at runtime.

---

## Running the Bot

### Check connectivity

```bash
python cli.py ping
```

### Place a MARKET order

```bash
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --qty 0.001
```

### Place a LIMIT order

```bash
python cli.py place --symbol ETHUSDT --side SELL --type LIMIT --qty 0.05 --price 3200
```

### Place a LIMIT order with custom TimeInForce

```bash
python cli.py place --symbol BTCUSDT --side BUY --type LIMIT --qty 0.001 --price 55000 --tif IOC
```

### Place a STOP-MARKET order (Bonus)

```bash
python cli.py place --symbol BTCUSDT --side SELL --type STOP_MARKET --qty 0.001 --stop-price 57000
```

### Place a STOP-LIMIT order (Bonus)

```bash
python cli.py place --symbol BTCUSDT --side SELL --type STOP --qty 0.001 --stop-price 57000 --price 56800
```

### List open orders

```bash
python cli.py orders                     # all open orders
python cli.py orders --symbol BTCUSDT   # filtered by symbol
```

### Cancel an order

```bash
python cli.py cancel --symbol BTCUSDT --order-id 4091823
```

### Launch interactive menu (Bonus)

```bash
python cli.py menu
```

### Enable verbose / debug console output

```bash
python cli.py -v place --symbol BTCUSDT --side BUY --type MARKET --qty 0.001
```

---

## Sample Output

### Successful MARKET order

```
────────────────────────────────────────────────────────────
  📋  ORDER REQUEST SUMMARY
────────────────────────────────────────────────────────────
  Symbol      : BTCUSDT
  Side        : BUY
  Type        : MARKET
  Quantity    : 0.001
────────────────────────────────────────────────────────────

────────────────────────────────────────────────────────────
  ✅  ORDER PLACED SUCCESSFULLY
────────────────────────────────────────────────────────────
  Order ID    : 4091823
  Client OID  : x-Cb7ytekJ4b3a7e12b0c4
  Symbol      : BTCUSDT
  Side        : BUY
  Type        : MARKET
  Status      : FILLED
  Qty (orig)  : 0.00100000
  Qty (exec)  : 0.00100000
  Avg Price   : 57832.50000000
  Time (ms)   : 1720617723510
────────────────────────────────────────────────────────────
```

### Validation error (no price for LIMIT)

```
Error: Price is required for this order type.
```

### Binance API error (invalid symbol)

```
  ❌  ORDER FAILED
  Binance error [-1121]: Invalid symbol.
```

---

## Logging

All activity is written to `logs/trading_bot.log`:

- **Console** — INFO level by default; DEBUG with `-v`
- **File** — always DEBUG; rotates at 5 MB, keeps 5 backups

Log format:
```
2025-07-10 14:22:03,572 | DEBUG    | bot.client                | ← POST /fapi/v1/order | status=200 | body={"orderId":4091823,...}
```

---

## Assumptions

| # | Assumption |
|---|-----------|
| 1 | **Testnet only.** The base URL is hardcoded to `https://testnet.binancefuture.com`. For production, change `BASE_URL` in `bot/client.py`. |
| 2 | **USDT-M Futures only.** Coin-M perpetuals and spot are not supported. |
| 3 | **No position management.** The bot places orders; tracking open positions or PnL is out of scope. |
| 4 | **Quantity precision.** The bot does not auto-round quantity to the symbol's `stepSize`. Ensure your quantity is valid for the pair (e.g. BTCUSDT min qty is 0.001). |
| 5 | **Single-threaded.** No concurrent order streaming; each CLI invocation is one blocking HTTP call. |

---

## Order Types Supported

| Type | Flag | Notes |
|------|------|-------|
| Market | `--type MARKET` | Executes immediately at best price |
| Limit | `--type LIMIT` | Requires `--price`; rests in order book |
| Stop-Market | `--type STOP_MARKET` | Requires `--stop-price`; triggers market order |
| Stop-Limit | `--type STOP` | Requires both `--stop-price` and `--price` |

---

## Requirements

```
requests>=2.31.0
```

No third-party Binance library is used — all API communication is direct REST via `requests`, giving full transparency over signing and request construction.