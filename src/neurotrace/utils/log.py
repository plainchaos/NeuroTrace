from __future__ import annotations

import logging


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%SZ",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


def task_start(logger: logging.Logger, name: str, details: str = "") -> None:
    msg = f"▶ {name}"
    if details:
        msg += f" — {details}"
    logger.info(msg)


def task_ok(logger: logging.Logger, name: str, seconds: float, details: str = "") -> None:
    msg = f"✔ {name} ({seconds:.2f}s)"
    if details:
        msg += f" — {details}"
    logger.info(msg)


def task_fail(logger: logging.Logger, name: str, err: str) -> None:
    logger.error(f"✖ {name} — {err}")


