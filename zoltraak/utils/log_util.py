import functools
import inspect
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Any

from tqdm import tqdm

import zoltraak
from zoltraak import settings

default_level = logging.INFO if settings.is_debug else logging.WARNING
logging.basicConfig(level=default_level)


# logging.Formatter のフォーマット指定子
#     %(name)s            ロガーの名前 (ロギングチャネル)
#     %(levelno)s         メッセージの数値ロギングレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)
#     %(levelname)s       メッセージのテキストロギングレベル ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
#     %(pathname)s        ロギング呼び出しが発行されたソースファイルのフルパス名 (利用可能な場合)
#     %(filename)s        パス名のファイル名部分
#     %(module)s          モジュール (ファイル名の名前部分)
#     %(lineno)d          ロギング呼び出しが発行されたソース行番号 (利用可能な場合)
#     %(funcName)s        関数名
#     %(created)f         LogRecord が作成された時刻 (time.time() の戻り値)
#     %(asctime)s         LogRecord が作成された時刻のテキスト表現
#     %(msecs)d           作成時刻のミリ秒部分
#     %(relativeCreated)d ロギングモジュールがロードされた時刻からの相対ミリ秒数 (通常はアプリケーションの起動時)
#     %(thread)d          スレッドID (利用可能な場合)
#     %(threadName)s      スレッド名 (利用可能な場合)
#     %(process)d         プロセスID (利用可能な場合)
#     %(message)s         record.getMessage() の結果、レコードが発行される直前に計算される
# PidFunctionFormatter.format() によるフォーマット指定子
#     %(file_name)s       log関連を除いた呼び出し元のファイル名
#     %(function_name)s   log関連を除いた呼び出し元の関数名

FORMATTER_CONSOLE = "%(asctime)s - %(file_name)s - %(function_name)s - %(levelname)s - %(message)s"
FORMATTER_WITH_PID = "%(asctime)s - PID:%(process)d - %(file_name)s - %(function_name)s - %(levelname)s - %(message)s"


def get_logger(name: str, level: int = default_level) -> logging.Logger:
    logger_ = logging.getLogger(name)
    logger_.propagate = False
    _add_handler(logger_, level=level)
    _add_file_handler(logger_, level=level)
    return logger_


# ロギング呼び出し関数を取るときに対象外とするソースファイルの名前部分
IGNORE_MODULES = ["__init__", "handlers", "log_util"]


class PidFunctionFormatter(logging.Formatter):
    def format(self, record):
        # プロセスIDを追加（processでいいかも）
        record.pid = os.getpid()
        # デフォルトのfuncNameではlog_iなどの共通部分しか出ないため、呼び出し元の関数名を取得する
        record.file_name, record.function_name = self.get_function_name()
        return super().format(record)

    def get_function_name(self) -> tuple[str, str]:
        frame = inspect.currentframe()
        while frame:
            if frame is None:
                return None
            code = frame.f_code  # コードオブジェクトを取得
            filename = os.path.basename(code.co_filename)
            filename_without_ext = os.path.splitext(filename)[0]
            # print("filename_without_ext=", filename_without_ext, ", code.co_name=", code.co_name)

            if filename_without_ext not in IGNORE_MODULES:
                return filename, code.co_name  # ファイル名と関数名を返す
            frame = frame.f_back
        return "unknown_file", "unknown_function"


def _add_handler(logger_: logging.Logger, level: int = default_level) -> logging.Logger:
    # コンソール出力用のハンドラの設定
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(level)
    formatter = PidFunctionFormatter(FORMATTER_CONSOLE)
    handler.setFormatter(formatter)
    logger_.addHandler(handler)


def _add_file_handler(
    logger_: logging.Logger, log_file: str = "zoltraak.log", level: int = default_level
) -> logging.Logger:
    # ファイルハンドラの設定
    file_handler = RotatingFileHandler(log_file, maxBytes=1024 * 1024, backupCount=5)  # 1MB, 最大5ファイル
    file_handler.setLevel(level)
    file_formatter = PidFunctionFormatter(FORMATTER_WITH_PID)
    file_handler.setFormatter(file_formatter)
    logger_.addHandler(file_handler)


logger = get_logger(zoltraak.__name__)

DEF_MAX_SHOW_RETURN_LEN = 100


def log_inout(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print("  --> " + f"Calling {func.__name__} with args: {args}, kwargs: {kwargs}")
        result = func(*args, **kwargs)
        if isinstance(result, str) and len(result) > DEF_MAX_SHOW_RETURN_LEN:
            print("  --> " + f"{func.__name__} returned: {result[:DEF_MAX_SHOW_RETURN_LEN]} ...")
        else:
            print("  --> " + f"{func.__name__} returned: {result}")
        return result

    return wrapper


def log_inout_info(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger_ = logging.getLogger(func.__name__)
        logger_.info(f"Calling {func.__name__} with args: {args}, kwargs: {kwargs}")
        result = func(*args, **kwargs)
        logger_.info(f"{func.__name__} returned: {result}")
        return result

    return wrapper


def log_inout_debug(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger_ = logging.getLogger(func.__name__)
        logger_.debug(f"Calling {func.__name__} with args: {args}, kwargs: {kwargs}")
        result = func(*args, **kwargs)
        logger_.debug(f"{func.__name__} returned: {result}")
        return result

    return wrapper


def log(msg: str, *args, **kwargs):
    if settings.is_debug:
        logger.info(msg, *args, **kwargs)


def log_e(msg: str, *args, **kwargs):
    logger.error(msg, *args, **kwargs)


def log_w(msg: str, *args, **kwargs):
    logger.warning(msg, *args, **kwargs)


def log_i(msg: str, *args, **kwargs):
    logger.info(msg, *args, **kwargs)


def log_d(msg: str, *args, **kwargs):
    logger.debug(msg, *args, **kwargs)


def log_head(title: str, msg: str, diff_n: int = 100):
    if settings.is_debug:
        separator_part = "\n" + "=" * 120 + "\n"
        title_part = f"{title}(冒頭{diff_n}字)" + separator_part
        msg_part = msg[:diff_n] + separator_part
        all_info = title_part + msg_part
        logger.info(all_info)


def log_head_diff(title: str, content1: str, content2: str, diff_n: int = 100):
    if settings.is_debug:
        separator_part = "\n" + "=" * 120 + "\n"
        title_part = f"{title}(冒頭{diff_n}字 差分)" + separator_part
        content1_part = content1[:diff_n] + separator_part
        diff_part = "  ---  ↓↓ 差分 ↓↓ ---  " + separator_part
        content2_part = content2[:diff_n] + separator_part
        all_info = title_part + content1_part + diff_part + content2_part
        logger.info(all_info)


def log_change(title: str, content1: str, content2: str):
    if settings.is_debug:
        separator_part = "\n" + "=" * 120 + "\n"
        title_part = f"{title}\n"
        content1_part = content1
        change_part = "\n  ---  ↓↓ ↓↓ ↓↓ ↓↓ ---  \n"
        content2_part = content2 + separator_part
        all_info = title_part + content1_part + change_part + content2_part
        logger.info(all_info)


def log_progress(t: tqdm):
    """tqdmオブジェクトから進捗率を計算し、ログに記録するコールバック関数"""
    progress = t.n / t.total
    log(f"Progress: {t.n}/{t.total} ({progress:.2%})")


def show_fully_qualified_name(obj: Any) -> str:
    module = inspect.getmodule(obj)
    # obj_name
    if hasattr(obj, "__qualname__"):  # noqa: SIM108
        obj_name = obj.__qualname__
    else:
        obj_name = str(obj)

    # fully_qualified_name
    if module is None or module.__name__ == "__main__":
        fully_qualified_name = obj_name
    else:
        fully_qualified_name = f"{module.__name__}.{obj_name}"
    print("fully_qualified_name=%s", fully_qualified_name)
