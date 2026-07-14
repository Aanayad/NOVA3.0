"""Nova 3.0 - centralized logging setup."""

import logging
import os
import sys


def setup_logging(level: str = "INFO") -> None:
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("logs/nova.log", encoding="utf-8"),
        ],
    )
