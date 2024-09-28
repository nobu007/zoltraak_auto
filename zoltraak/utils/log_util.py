import functools
import logging

import zoltraak
from zoltraak import settings

if settings.is_debug:
    level = logging.INFO
else:
    level = logging.ERROR
logging.basicConfig(level=level)

logger = logging.getLogger(zoltraak.__name__)


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


def log(content: str):
    if settings.is_debug:
        logger.info(content)
