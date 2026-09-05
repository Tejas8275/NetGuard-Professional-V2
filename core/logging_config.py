"""Local, rotating diagnostic logs that never block the application."""
import logging
from logging.handlers import RotatingFileHandler

from core.storage import APP_DATA_DIR

LOGGER_NAME = 'netguard'


def get_logger():
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    try:
        APP_DATA_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
        handler = RotatingFileHandler(APP_DATA_DIR / 'netguard.log', maxBytes=1_000_000, backupCount=3, encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s'))
        logger.addHandler(handler)
    except OSError:
        logger.addHandler(logging.NullHandler())
    return logger
