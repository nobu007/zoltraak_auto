import os
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import zoltraak.llms.litellm_api as litellm
from zoltraak.schema.schema import MagicInfo
from zoltraak.utils.subprocess_util import SubprocessUtil

console = Console()
console = Console(width=120)  # ターミナルの幅


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
                console.print(Panel(magic_info.success_message, style="green"))
            else:
                console.print(Panel(f"{magic_info.error_message}\n{result.stderr}", style="red"))
            return result  # noqa: TRY300
        except SubprocessUtil.CalledProcessError as e:
            console.print(Panel(f"{magic_info.error_message}\n{e}", style="red"))
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
            console.print(Panel(magic_info.success_message, style="green"))
            return result  # noqa: TRY300
        except Exception as e:
            console.print(Panel(f"{magic_info.error_message}\n{e}", style="red"))
            raise
    return None


def display_magic_info_pre(magic_info: MagicInfo):
    """
    これから実行する魔法術式の情報を整形して表示します。
    """
    table = Table(title=magic_info.description, title_style="bold")
    table.add_column("項目", style="cyan", no_wrap=True)
    table.add_column("内容", style="magenta")

    table.add_row("起動術式 (プロンプトコンパイラ)", magic_info.grimoire_compiler)
    table.add_row("魔法術式 (要件定義書)", magic_info.file_info.target_file_path)
    table.add_row("錬成術式 (プロンプトフォーマッタ)", magic_info.grimoire_formatter)
    table.add_row("領域術式 (領域作成+コード展開)", magic_info.grimoire_architect)
    table.add_row("言霊   (LLMモデル名) ", magic_info.model_name)

    console.print(Panel(table, title="魔法術式情報(構築中)", border_style="green"))


def display_magic_info_post(magic_info: MagicInfo):
    """
    実行した魔法術式の情報を整形して表示します。
    """
    table = Table(title="MagicInfo", title_style="bold")
    table.add_column("項目", style="cyan", no_wrap=True)
    table.add_column("内容", style="magenta")

    table.add_row("完了術式", magic_info.current_grimoire_name)
    table.add_row("魔法術式 (要件定義書)", magic_info.file_info.target_file_path)
    table.add_row("領域", magic_info.file_info.target_dir)

    console.print(Panel(table, title="魔法術式情報(完了)", border_style="green"))


def display_magic_info_full(magic_info: MagicInfo):
    """
    実行した魔法術式の情報を整形して表示します。
    """
    table = Table(title="MagicInfoFull", title_style="bold")
    table.add_column("項目", style="cyan", no_wrap=True)
    table.add_column("内容", style="magenta")

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

    console.print(Panel(table, title="魔法術式情報(詳細)", border_style="white"))


def add_file_info_full(file_info: dict, table: Table) -> None:
    """
    実行した魔法術式の情報(FileInfo)を整形して追加します。
    """
    for key, value in file_info.items():
        table.add_row("  " + key, str(value))


def display_info_full(any_info: BaseModel, title: str = "詳細", table_title: str = ""):
    """
    実行した魔法術式の情報を整形して表示します。
    """
    table = Table(title=table_title, title_style="bold")
    table.add_column("項目", style="cyan", no_wrap=True)
    table.add_column("内容", style="magenta")

    for key, value in any_info.model_dump().items():
        table.add_row(key, str(value))

    console.print(Panel(table, title=title, border_style="white"))


def display_magic_info_final(magic_info: MagicInfo):
    """
    実行した領域術式の情報を整形して表示します。
    """
    table = Table(title="領域術式", title_style="bold")
    table.add_column("項目", style="cyan", no_wrap=True)
    table.add_column("内容", style="magenta")

    table.add_row("絶対空間", magic_info.file_info.work_dir)
    table.add_row("領域名", magic_info.file_info.canonical_name)
    _add_row_relpath(table, "領域情報", magic_info.file_info.target_dir, magic_info.file_info.work_dir)
    table.add_row("魔導書名", magic_info.current_grimoire_name)
    _add_row_relpath(table, "錬成器", magic_info.grimoire_compiler, magic_info.file_info.work_dir)
    _add_row_relpath(table, "起動式", magic_info.grimoire_architect, magic_info.file_info.work_dir)
    _add_row_relpath(table, "調律石", magic_info.grimoire_formatter, magic_info.file_info.work_dir)
    _add_row_relpath(table, "魔法術式 (錬成前)", magic_info.file_info.source_file_path, magic_info.file_info.work_dir)
    _add_row_relpath(table, "魔法術式 (錬成後)", magic_info.file_info.target_file_path, magic_info.file_info.work_dir)

    console.print(Panel(table, title="魔法術式情報(完了)", border_style="green"))


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
