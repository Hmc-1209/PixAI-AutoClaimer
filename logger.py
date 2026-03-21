import os
import logging
from datetime import datetime, timezone

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")


def get_logger(name: str = "pixai") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S UTC",
    )
    formatter.converter = lambda *args: datetime.now(timezone.utc).timetuple()

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    _update_file_handler(logger, formatter)

    return logger


def _update_file_handler(logger: logging.Logger, formatter: logging.Formatter):
    os.makedirs(LOG_DIR, exist_ok=True)
    # Monthly granularity: 2026-03.log
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    log_path = os.path.join(LOG_DIR, f"{month}.log")

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)

    for handler in logger.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            handler.close()
            logger.removeHandler(handler)

    logger.addHandler(file_handler)


def ensure_monthly_handler(logger: logging.Logger):
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            current = os.path.basename(handler.baseFilename).replace(".log", "")
            if current == month:
                return

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S UTC",
    )
    formatter.converter = lambda *args: datetime.now(timezone.utc).timetuple()
    _update_file_handler(logger, formatter)


# Backwards-compat alias used in main.py / monitor.py
ensure_yearly_handler = ensure_monthly_handler
