import os
from collections.abc import Callable
from datetime import datetime
from typing import Any

from pydantic import BaseModel
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import zoltraak.llms.litellm_api as litellm
from zoltraak.schema.schema import MagicInfo
from zoltraak.utils.subprocess_util import SubprocessUtil

# 通常のConsoleオブジェクト
console = Console(width=120)
# ファイル出力用のConsoleオブジェクト
with open("rich.log", "a", encoding="utf-8") as log_file:
    file_console = Console(width=300, file=open("rich.log", "a", encoding="utf-8"))  # noqa: SIM115


# loggingのハンドラが使えなそうなので独自のハンドラもどきを作成（RichHandler＋loggerはダメそう）
# 暇ができたらトライしたい
# 参考： https://qiita.com/bounoki/items/a34da7ac3be867b037fe
def console_print_all(*args, **kwargs):
    console.print(*args, **kwargs)
    file_console.print(*args, **kwargs)


def run_command_with_spinner(
    magic_info: MagicInfo, command: list[str], *, check: bool = False
) -> SubprocessUtil.CompletedProcess:
    """
    指定されたコマンドを実行し、その間スピナーを表示します。
    """
    with console.status(f"[bold green]{magic_info.description}"):
        try:
            result = SubprocessUtil.run(command, shell=False, check=check, capture_output=True, text=True)
            if result.returncode == 0:
                console_print_all(Panel(magic_info.success_message, style="green"))
            else:
                console_print_all(Panel(f"{magic_info.error_message}\n{result.stderr}", style="red"))
            return result  # noqa: TRY300
        except SubprocessUtil.CalledProcessError as e:
            console_print_all(Panel(f"{magic_info.error_message}\n{e}", style="red"))
            raise
    return None


def run_function_with_spinner(magic_info: MagicInfo, func: Callable[..., Any], *args, **kwargs) -> Any:
    """
    指定された関数を実行し、その間スピナーを表示します。

    :param magic_info: MagicInfo
    :param func: 実行する関数
    :param args: 関数に渡す位置引数
    :param kwargs: 関数に渡すキーワード引数
    :return: 関数の戻り値
    """
    with console.status(f"[bold green]{magic_info.description}"):
        try:
            result = func(*args, **kwargs)
            console_print_all(Panel(magic_info.success_message, style="green"))
            return result  # noqa: TRY300
        except Exception as e:
            console_print_all(Panel(f"{magic_info.error_message}\n{e}", style="red"))
            raise
    return None


def prepare_table_common(title: str, title_style: str = "bold") -> Table:
    table = Table(title="title", title_style=title_style)
    table.title = title
    table.title_style = title_style
    table.add_column("項目", style="cyan", no_wrap=True)

    # ローカルマシンに設定されているタイムゾーンを取得
    local_tz = datetime.now().astimezone().tzinfo
    table.caption = f"取得日時: {datetime.now(tz=local_tz).strftime('%Y-%m-%d %H:%M:%S')}"
    table.caption_justify = "left"
    table.title = f"{title} 取得日時: {datetime.now(tz=local_tz).strftime('%Y-%m-%d %H:%M:%S')}"
    return table


def display_magic_info_init(magic_info: MagicInfo):
    """
    初期の魔法術式の情報を整形して表示します。
    """
    table = prepare_table_common("MagicInfo(初期値)")

    file_info = magic_info.file_info
    table.add_row("自然言語 (ユーザー入力.md)", file_info.prompt_file_path_abs)
    table.add_row("起動術式 (ユーザ要求記述書.md)", file_info.pre_md_file_path_abs)
    table.add_row("魔法術式 (要件定義書.md)", file_info.md_file_path_abs)
    table.add_row("古代魔導書 (高級言語プログラム)", file_info.py_file_path_abs)
    table.add_row("制御方式(モード) ", magic_info.magic_mode)
    table.add_row("術式階層(レイヤ) ", magic_info.magic_layer)

    console_print_all(Panel(table, title="魔法術式情報(構築中)", border_style="green"))


def display_magic_info_pre(magic_info: MagicInfo):
    """
    これから実行する魔法術式の情報を整形して表示します。
    """
    table = prepare_table_common(magic_info.description)

    table.add_row("起動術式 (プロンプトコンパイラ)", magic_info.grimoire_compiler)
    table.add_row("魔法術式 (要件定義書)", magic_info.file_info.target_file_path)
    table.add_row("錬成術式 (プロンプトフォーマッタ)", magic_info.grimoire_formatter)
    table.add_row("領域術式 (領域作成+コード展開)", magic_info.grimoire_architect)
    table.add_row("言霊   (LLMモデル名) ", magic_info.model_name)

    console_print_all(Panel(table, title="魔法術式情報(構築中)", border_style="green"))


def display_magic_info_post(magic_info: MagicInfo):
    """
    実行した魔法術式の結果を表示します。
    """
    table = prepare_table_common("MagicInfo(結果)")

    table.add_row("完了術式", magic_info.current_grimoire_name)
    table.add_row("魔法術式 (要件定義書)", magic_info.file_info.target_file_path)
    table.add_row("領域", magic_info.file_info.target_dir)

    console_print_all(Panel(table, title="魔法術式情報(完了)", border_style="green"))


def add_file_info_full(file_info: dict, table: Table) -> None:
    """
    魔法術式の情報(FileInfo)を整形して追加します。
    """
    for key, value in file_info.items():
        table.add_row("  " + key, str(value))


def display_magic_info_full(magic_info: MagicInfo):
    """
    魔法術式の情報を整形して表示します。
    """
    table = prepare_table_common("MagicInfo(FULL)")

    for key, value in magic_info.model_dump().items():
        if key == "file_info":
            table.add_row(key, "<<==== FileInfo start ====>>")
            add_file_info_full(value, table)
            table.add_row(key, "<<==== FileInfo  end  ====>>")
            continue
        if key == "prompt":
            # プロンプトは長くなることがあるので、100文字までに制限
            table.add_row(key, str(value[:100]))
            continue
        table.add_row(key, str(value))

    console_print_all(Panel(table, title="魔法術式情報(詳細)", border_style="white"))


def display_info_full(any_info: BaseModel, title: str = "詳細", table_title: str = ""):
    """
    魔法術式の情報を整形して表示します。
    """
    table = prepare_table_common(table_title)

    for key, value in any_info.model_dump().items():
        table.add_row(key, str(value))

    console_print_all(Panel(table, title=title, border_style="white"))


def display_magic_info_intermediate(magic_info: MagicInfo):
    """
    実行した領域術式の中間結果を整形して表示します。
    """
    table = prepare_table_common("領域術式(途中経過)")

    table.add_row("絶対空間", magic_info.file_info.work_dir)
    table.add_row("領域名", magic_info.file_info.canonical_name)
    _add_row_relpath(table, "領域情報", magic_info.file_info.target_dir, magic_info.file_info.work_dir)
    _add_row_relpath(table, "魔法術式 (錬成前)", magic_info.file_info.source_file_path, magic_info.file_info.work_dir)
    _add_row_relpath(table, "魔法術式 (錬成後)", magic_info.file_info.target_file_path, magic_info.file_info.work_dir)

    console_print_all(Panel(table, title="術式情報", border_style="green"))


def display_magic_info_final(magic_info: MagicInfo):
    """
    実行した領域術式の最終結果を整形して表示します。
    """
    table = prepare_table_common("領域術式(結果)")

    table.add_row("絶対空間", magic_info.file_info.work_dir)
    table.add_row("領域名", magic_info.file_info.canonical_name)
    _add_row_relpath(table, "領域情報", magic_info.file_info.target_dir, magic_info.file_info.work_dir)
    table.add_row("魔導書名", magic_info.current_grimoire_name)
    _add_row_relpath(table, "錬成器", magic_info.grimoire_compiler, magic_info.file_info.work_dir)
    _add_row_relpath(table, "起動式", magic_info.grimoire_architect, magic_info.file_info.work_dir)
    _add_row_relpath(table, "調律石", magic_info.grimoire_formatter, magic_info.file_info.work_dir)
    _add_row_relpath(table, "魔法術式 (錬成前)", magic_info.file_info.source_file_path, magic_info.file_info.work_dir)
    _add_row_relpath(table, "魔法術式 (錬成後)", magic_info.file_info.target_file_path, magic_info.file_info.work_dir)

    console_print_all(Panel(table, title="魔法術式情報(完了)", border_style="green"))


def _add_row_relpath(table: Table, key: str, path: str, base_path: str) -> None:
    abs_path = os.path.abspath(path)
    abs_base_path = os.path.abspath(base_path)
    rel_path = os.path.relpath(abs_path, abs_base_path)
    table.add_row(key, rel_path)


def generate_response_with_spinner(
    magic_info: MagicInfo,
):
    """
    スピナーを表示しながらコマンドを実行し、結果を表示します。
    """
    display_magic_info_pre(magic_info)
    result = run_function_with_spinner(magic_info, generate_response, magic_info.model_name, magic_info.prompt)
    display_magic_info_post(magic_info)
    if result is None:
        return "グリモアの展開に失敗しました"

    return result


def generate_response(model_name: str, prompt: str) -> str:
    """
    promptを指定してllmからのレスポンスを生成する関数
    """
    return litellm.generate_response(model_name, prompt, 4000, 0.7)
