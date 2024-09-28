import subprocess
import threading
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typing import List, Callable, Any
import zoltraak.llms.litellm_api as litellm
from pydantic import BaseModel, Field
from zoltraak import settings

console = Console()


class FileInfo(BaseModel):
    # 識別子
    canonical_name: str = Field(
        default="", description="対象のファイル群をシステム全体で一意に識別するための標準的な名前"
    )

    # Inputファイル
    md_file_path: str = Field(default="", description="処理対象のmdファイル")
    py_file_path: str = Field(default="", description="処理対象のpyファイル")

    # 処理対象ファイル
    source_file_path: str = Field(default="", description="ソースファイルパス")
    target_file_path: str = Field(default="", description="処理対象のファイルパス")
    past_source_file_path: str = Field(default="", description="過去のソースファイル")

    past_target_file_path: str = Field(default="", description="過去の出力先ファイル")
    past_source_folder: str = Field(default="past_md_files", description="過去のソースフォルダ")
    target_dir: str = Field(default="./output", description="出力先のディレクトリ")

    # その他
    source_hash: str = Field(default="", description="ソースファイルのハッシュ値")


class MagicInfo(BaseModel):
    # grimoire関連
    current_grimoire_name: str = Field(default="default_grimoire.md", description="現在のグリモアの名前")
    description: str = Field(default="汎用魔法式を展開します", description="現在のグリモアの説明")
    grimoire_compiler: str = Field(default="dev_obj.md", description="使用するグリモアコンパイラのファイル名")
    grimoire_architect: str = Field(
        default="architect_claude.md", description="使用するグリモアアーキテクトのファイル名"
    )
    grimoire_formatter: str = Field(
        default="md_comment.md", description="使用するグリモアフォーマッタのファイル名(=language)"
    )

    # file関連
    file_info: FileInfo = Field(default=FileInfo(), description="入出力ファイル情報")

    # その他
    model_name: str = Field(default=settings.model_name, description="使用するLLMモデルの名前")
    prompt: str = Field(default="", description="使用するグリモアのプロンプト")
    success_message: str = Field(default="魔法式の構築が完了しました。", description="グリモア成功時のメッセージ")
    error_message: str = Field(
        default="魔法式の構築中にエラーが発生しました。", description="グリモア失敗時のメッセージ"
    )
    language: str = Field(default="", description="汎用言語指定(現状ではgrimoire_formatterに影響)")


def run_command_with_spinner(
    magic_info: MagicInfo, command: List[str], check: bool = False
) -> subprocess.CompletedProcess:
    """
    指定されたコマンドを実行し、その間スピナーを表示します。
    """
    with console.status(f"[bold green]{magic_info.description}"):
        try:
            result = subprocess.run(command, check=check, capture_output=True, text=True)
            if result.returncode == 0:
                console.print(Panel(magic_info.success_message, style="green"))
            else:
                console.print(Panel(f"{magic_info.error_message}\n{result.stderr}", style="red"))
            return result  # noqa: TRY300
        except subprocess.CalledProcessError as e:
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
    table.add_row("領域術式 (領域作成＋コード展開)", magic_info.grimoire_architect)
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


def generate_response_with_spinner(
    magic_info: MagicInfo,
):
    """
    スピナーを表示しながらコマンドを実行し、結果を表示します。
    """
    display_magic_info_pre(magic_info)
    result = run_function_with_spinner(magic_info, generate_response, magic_info.model_name, magic_info.prompt)
    display_magic_info_post(magic_info)
    if result == None:
        return "グリモアの展開に失敗しました"

    return result


def generate_response(model_name: str, prompt: str) -> str:
    """
    promptを指定してllmからのレスポンスを生成する関数
    """
    return litellm.generate_response(model_name, prompt, 4000, 0.7)
