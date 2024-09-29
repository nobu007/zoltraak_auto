import functools
import logging
import sys

import zoltraak
from zoltraak import settings

default_level = logging.INFO if settings.is_debug else logging.WARNING
logging.basicConfig(level=default_level)


def get_logger(name: str, level: int = default_level) -> logging.Logger:
    logger = logging.getLogger(name)
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(level)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    return logger


logger = get_logger(zoltraak.__name__)


def log_inout(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print("  --> " + f"Calling {func.__name__} with args: {args}, kwargs: {kwargs}")
        result = func(*args, **kwargs)
        print("  --> " + f"{func.__name__} returned: {result}")
        return result

    return wrapper


def log_inout_info(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__name__)
        logger.info(f"Calling {func.__name__} with args: {args}, kwargs: {kwargs}")
        result = func(*args, **kwargs)
        logger.info(f"{func.__name__} returned: {result}")
        return result

    return wrapper


def log_inout_debug(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__name__)
        logger.debug(f"Calling {func.__name__} with args: {args}, kwargs: {kwargs}")
        result = func(*args, **kwargs)
        logger.debug(f"{func.__name__} returned: {result}")
        return result

    return wrapper


def log(msg: str, *args, **kwargs):
    if settings.is_debug:
        logger.info(msg, *args, **kwargs)


def log_w(msg: str, *args, **kwargs):
    logger.warning(msg, *args, **kwargs)


def log_i(msg: str, *args, **kwargs):
    logger.info(msg, *args, **kwargs)


def log_d(msg: str, *args, **kwargs):
    logger.debug(msg, *args, **kwargs)
