import logging
import logging.handlers
import os
from pathlib import Path


LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "trading_bot.log"

# ── Formatters ──────────────────────────────────────────────────────────────

FILE_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s"
)
CONSOLE_FORMAT = "%(levelname)-8s %(message)s"


def setup_logging(verbose: bool = False) -> None:

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)          # capture everything; handlers filter

    # ── Rotating file handler (always DEBUG) ─────────────────────────────────
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,         # 5 MB per file
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(FILE_FORMAT))

    # ── Console handler ───────────────────────────────────────────────────────
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(logging.Formatter(CONSOLE_FORMAT))

    # avoid duplicate handlers if called more than once (e.g. in tests)
    if not root.handlers:
        root.addHandler(file_handler)
        root.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """Return a named child logger."""
    return logging.getLogger(name)