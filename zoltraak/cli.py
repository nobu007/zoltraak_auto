import argparse
import os
import os.path
import sys

import zoltraak
import zoltraak.llms.litellm_api as litellm
from zoltraak import settings
from zoltraak.converter.base_converter import BaseConverter
from zoltraak.converter.converter import MarkdownToPythonConverter
from zoltraak.converter.md_converter import MarkdownToMarkdownConverter
from zoltraak.core.magic_workflow import MagicWorkflow
from zoltraak.schema.schema import MagicInfo, MagicLayer, MagicMode, ZoltraakParams
from zoltraak.utils.file_util import FileUtil
from zoltraak.utils.grimoires_util import GrimoireUtil
from zoltraak.utils.log_util import log
from zoltraak.utils.rich_console import display_info_full, display_magic_info_final
from zoltraak.utils.subprocess_util import SubprocessUtil


def main() -> None:
    """メイン処理(args前処理、コンパイラー確認、パラメータ設定)"""
    log("")
    log("========================================")
    log("||         zoltraak cli start         ||")
    log("========================================")
    parser = argparse.ArgumentParser(
        description="MarkdownファイルをPythonファイルに変換します", formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("input", help="変換対象のMarkdownファイルのパスまたはテキスト", nargs="?")
    parser.add_argument("--output-dir", help="生成されたPythonファイルの出力ディレクトリ", default="generated")
    parser.add_argument("-p", "--prompt", help="追加のプロンプト情報", default="")
    parser.add_argument("-c", "--compiler", help="コンパイラー（要件定義書のテンプレート）", default="")
    parser.add_argument("-f", "--formatter", help="コードフォーマッター", default="md_comment")
    parser.add_argument("-cc", "--custom-compiler", help="自作コンパイラー（自作定義書生成文書）", default="")
    parser.add_argument(
        "-v", "--version", action="store_true", help="バージョン情報を表示"
    )  # 追加: バージョン情報表示オプション
    parser.add_argument("-l", "--language", help="出力言語を指定", default="")  # 追加: 汎用言語指定オプション
    parser.add_argument("-m", "--model_name", help="使用するモデルの名前", default="")
    parser.add_argument(
        "-n", "--canonical_name", help="アウトプットファイルやフォルダを一意に識別するための正規名称", default=""
    )
    parser.add_argument(
        "-mm",
        "--magic_mode",
        type=MagicMode,
        choices=list(MagicMode),
        help=MagicMode.get_description(),
        default=MagicMode.GRIMOIRE_AND_PROMPT,
    )
    parser.add_argument(
        "-ml",
        "--magic_layer",
        type=str,
        help=MagicLayer.get_description(),
        default=str(MagicLayer.LAYER_3_REQUIREMENT_GEN),
    )
    args = parser.parse_args()
    if args.version:  # バージョン情報表示オプションが指定された場合
        show_version_and_exit()  # - バージョン情報を表示して終了

    if args.input is None:  # 入力ファイルまたはテキストが指定されていない場合
        show_usage_and_exit()  # - 使用方法を表示して終了

    if args.model_name:  # -- 使用するモデルの名前が指定された場合
        settings.model_name = args.model_name  # -- zoltraak全体設定に保存してどこからでも使えるようにする

    # args表示
    show_args(args)

    # compiler_path確定
    compiler_path = prepare_compiler(args.input, args.compiler, args.custom_compiler)

    params = ZoltraakParams()
    params.input = args.input
    params.prompt = args.prompt
    params.compiler = compiler_path  # compilerとcustom_compilerを集約(絶対パス)
    params.formatter = args.formatter
    params.language = args.language
    params.model_name = args.model_name
    params.canonical_name = args.canonical_name
    params.magic_mode = args.magic_mode
    params.magic_layer = args.magic_layer
    preprocess_input(params)
    display_info_full(params, title="ZoltraakParams")
    main_exec(params)


def preprocess_input(params: ZoltraakParams) -> None:
    log("params.input=" + params.input)
    # input は canonical_name または promptが入る
    # この関数ではinputからcanonical_name、promptを決定する
    # 以降はinputを参照しないこと！
    preprocess_input_canonical_name(params)
    preprocess_input_prompt(params)


def preprocess_input_canonical_name(params: ZoltraakParams) -> None:
    log("params.input=" + params.input)
    # ---- canonical_nameの決定ロジック ----
    # canonical_name は params ⇒ input ⇒デフォルト値(空白) の順に優先して設定

    default_canonical_name = ""  # ここでデフォルトを空白にしているのはprocess_text_input()への分岐判定のため
    canonical_name = default_canonical_name

    if params.canonical_name:
        # paramsから決める
        canonical_name = params.canonical_name
    elif params.input.endswith(".md"):
        # inputから決める
        canonical_name = os.path.basename(params.input)
    params.canonical_name = canonical_name
    log("canonical_name: %s", params.canonical_name)

    # 初回になければ作成対象のファイルを生成する
    original_md_file_path = os.path.abspath(params.canonical_name)
    if not os.path.isfile(original_md_file_path):
        FileUtil.write_file(original_md_file_path, "")


def preprocess_input_prompt(params: ZoltraakParams) -> None:
    # ---- promptの決定ロジック ----
    # 1. promptが引数で指定済みならそのまま採用
    # 2. inputが有効、かつmdファイル以外ならpromptとして採用
    # 3. canonical_nameで指定されたmdの中身があれば、promptは空で確定
    # 4. promptは未定かつmdも空なのでエラー終了

    # promptが引数で指定済みならそのまま採用
    if params.prompt:
        return

    # inputが有効、かつmdファイル以外ならpromptとして採用
    if params.input and not params.input.endswith(".md"):
        params.prompt = params.input
        return

    # canonical_nameで指定されたmdの中身があれば、promptは空で確定
    if FileUtil.has_content(params.canonical_name, 10):
        return

    # promptは未定かつmdも空なのでエラー終了
    show_usage_and_exit()


def main_exec(params: ZoltraakParams) -> None:
    """メイン処理(メイン処理実行)"""
    if params.canonical_name:
        magic_info = process_markdown_file(params)
        display_magic_info_final(magic_info)
    else:
        # canonical_nameが未確定ならテキスト入力から確定させてから再実行
        zoltraak_command = process_text_input(params)  # - テキスト入力を処理する関数を呼び出す
        log("zoltraak_command=" + zoltraak_command)  # - 実行したzoltraakコマンドを表示 (デバッグ用)

    # llm使用量を表示
    litellm.show_used_total_tokens()


def prepare_compiler(input_: str, compiler: str, custom_compiler: str) -> str:
    if compiler and custom_compiler:  # -- デフォルトのコンパイラーとカスタムコンパイラーの両方が指定されている場合
        show_compiler_conflict_error_and_exit()  # --- コンパイラー競合エラーを表示して終了

    # compilerが有効かチェック
    return GrimoireUtil.prepare_compiler(input_, compiler, custom_compiler)


def show_version_and_exit():
    print(f"zoltraak version {zoltraak.__version__}")
    sys.exit(0)


def show_usage_and_exit():
    print("\033[31mエラー: 入力ファイルまたはテキストが指定されていません。\033[0m")
    print("\033[92m使用方法: zoltraak <mdファイルのパス または テキスト> [オプション]\033[0m")
    print('\033[33m例1:\033[0m zoltraak calc.md -p "ドローンを用いた競技システムを考える" -c dev_obj')
    print("  説明: calc.mdファイルを入力とし、ドローンを用いた競技システムの要件定義書を生成します。")
    print("        オブジェクト指向設計のコンパイラー（dev_obj）を使用します。")
    print('\033[33m例2:\033[0m zoltraak "タクシーの経営課題を解決するための戦略ドキュメントを作成する" -c biz_consult')
    print("  説明: プロンプトテキストを入力とし、タクシー会社の経営課題解決のための戦略ドキュメントを生成します。")
    print("        ビジネスコンサルティング用のコンパイラー（biz_consult）を使用します。")
    print('\033[33m例3:\033[0m zoltraak "レストランの予約管理システムの要件定義書" -cc custom_compiler.md')
    print("  説明: プロンプトテキストを入力とし、レストランの予約管理システムの要件定義書を生成します。")
    print("        カスタムコンパイラー（custom_compiler.md）を使用します。")
    sys.exit(1)


def show_compiler_error_and_exit():
    print("\033[31mエラー: コンパイラーが指定されていません。\033[0m")
    print("-c オプションでデフォルトのコンパイラーを指定するか、")
    print("-cc オプションで自作のコンパイラー（要件定義書のテンプレート）のファイルパスを指定してください。")
    print("\033[92mデフォルトのコンパイラー:\033[0m")
    print("\033[33m- dev_obj: オブジェクト指向設計を用いた開発タスクに関する要件定義書を生成するコンパイラ\033[0m")
    print(
        """  説明: オブジェクト指向の原則に基づいて、開発タスクの要件定義書を生成します。
        クラス図、シーケンス図、ユースケースなどを含みます。"""
    )
    print("\033[33m- dev_func: 関数型プログラミングを用いた開発タスクに関する要件定義書を生成するコンパイラ\033[0m")
    print(
        """  説明: 関数型プログラミングの原則に基づいて、開発タスクの要件定義書を生成します。
        純粋関数、不変性、高階関数などの概念を取り入れます。"""
    )
    print("\033[33m- biz_consult: ビジネスコンサルティングに関するドキュメントを生成するコンパイラ\033[0m")
    print(
        """  説明: 企業の課題解決や戦略立案のためのコンサルティングドキュメントを生成します。
        市場分析、SWOT分析、アクションプランなどを含みます。"""
    )
    print("\033[33m- general_def: 一般的な開発タスクに関する要件定義書を生成するコンパイラ\033[0m")
    print(
        """  説明: 様々な開発タスクに対応した汎用的な要件定義書を生成します。
        システムの目的、機能要件、非機能要件などを網羅します。"""
    )
    print("\033[33m- general_reqdef: 一般的な要求事項に関する要件定義書を生成するコンパイラ\033[0m")
    print(
        """  説明: システム開発以外の一般的な要求事項について、要件定義書を生成します。
        プロジェクトの目標、スコープ、制約条件などを明確にします。"""
    )
    sys.exit(1)


def show_compiler_conflict_error_and_exit():
    print("\033[31mエラー: -c オプションと -cc オプションは同時に指定できません。\033[0m")
    sys.exit(1)


def show_args(args: argparse.Namespace):
    for arg, value in vars(args).items():
        if value:
            log(f"args.{arg}={value}")


def process_markdown_file(params: ZoltraakParams) -> MagicInfo:
    """
    Markdownファイルを処理する
    前提： params.input で処理対象のmarkdownファイルが指定される
    """
    output_dir_abs = os.path.abspath(params.output_dir)

    compiler_path = os.path.abspath(params.compiler)
    architect_path = GrimoireUtil.get_valid_architect("architect_claude.md")
    formatter_path = GrimoireUtil.get_valid_formatter(params.formatter)

    canonical_name = params.canonical_name
    md_file_path = canonical_name
    py_file_path = ""
    py_file_path = os.path.splitext(md_file_path)[0] + ".py"  # Markdownファイルの拡張子を.pyに変更

    # 絶対パスに変換
    md_file_path = os.path.abspath(md_file_path)
    py_file_path = os.path.abspath(py_file_path)

    # ここはMagicInfoの定義順に初期化すること！
    magic_info = MagicInfo()
    magic_info.magic_mode = params.magic_mode
    magic_info.magic_layer = MagicLayer.new(params.magic_layer)
    magic_info.model_name = settings.model_name
    magic_info.prompt_input = params.prompt
    magic_info.current_grimoire_name = canonical_name
    magic_info.description = ""  # デフォルト値を使う
    magic_info.grimoire_compiler = compiler_path
    magic_info.grimoire_architect = architect_path
    magic_info.grimoire_formatter = formatter_path

    # file関連
    magic_info.file_info.md_file_path = md_file_path
    magic_info.file_info.py_file_path = py_file_path
    magic_info.file_info.update_work_dir()
    magic_info.file_info.update()
    magic_info.file_info.canonical_name = canonical_name
    magic_info.file_info.target_dir = output_dir_abs

    # その他
    magic_info.success_message = ""  # 後で設定する
    magic_info.error_message = ""  # 後で設定する
    magic_info.language = params.language
    magic_info.is_debug = False

    magic_workflow = MagicWorkflow(magic_info)

    converter = create_converter(magic_workflow)
    os.makedirs(
        os.path.dirname(py_file_path), exist_ok=True
    )  # Pythonファイルの出力ディレクトリを作成（既に存在する場合は何もしない）
    new_file_path = magic_workflow.run(converter.convert_loop)
    magic_info.file_info.final_output_file_path = new_file_path
    return magic_info


# TO_MARKDOWN_CONVERTER を使うレイヤの一覧
TO_MARKDOWN_CONVERTER_LAYER_LIST = [MagicLayer.LAYER_1_REQUEST_GEN, MagicLayer.LAYER_2_REQUIREMENT_GEN]


def create_converter(magic_workflow: MagicWorkflow) -> BaseConverter:
    log("magic_info.magic_layer=%s", magic_workflow.magic_info.magic_layer)
    if magic_workflow.magic_info.magic_layer in TO_MARKDOWN_CONVERTER_LAYER_LIST:
        # マークダウンに変換するコンバータを使う
        log("MarkdownToMarkdownConverter")
        return MarkdownToMarkdownConverter(magic_workflow)
    # pythonに変換するコンバータを使う
    log("MarkdownToPythonConverter")
    return MarkdownToPythonConverter(magic_workflow)


def get_custom_compiler_path(custom_compiler):
    compiler_path = os.path.abspath(custom_compiler)
    if not os.path.exists(compiler_path):
        print(f"\033[31mエラー: 指定されたカスタムコンパイラーのファイル '{compiler_path}' が存在しません。\033[0m")
        print("\033[33m以下の点を確認してください:\033[0m")
        print("1. ファイルが指定されたパスに存在することを確認してください。")
        print("2. カスタムコンパイラーのファイルパスが正しいことを確認してください。")
        print("3. ファイル名の拡張子が '.md' であることを確認してください。")
        print("4. ファイルの読み取り権限があることを確認してください。")
    # print(f"カスタムコンパイラー: {compiler_path}")
    return compiler_path


def process_text_input(params: ZoltraakParams) -> str:
    # 要件定義書の名前をinputから新規に作成する
    next_prompt = params.input
    md_file_path = generate_md_file_name(next_prompt)

    # コマンドを再発行する
    params.input = md_file_path
    params.prompt = next_prompt
    zoltraak_command = params.get_zoltraak_command()
    SubprocessUtil.run_shell_command(zoltraak_command)
    return zoltraak_command


def generate_md_file_name(prompt):
    # promptからファイル名を生成するためにgenerate_response関数を利用

    print("検索結果生成中...")

    # requirementsディレクトリが存在しない場合は作成する
    requirements_dir = "requirements"
    if not os.path.exists(requirements_dir):
        os.makedirs(requirements_dir)

    # zoltraak/requirements/内のファイル名を全て取得
    existing_files = [file for file in os.listdir(requirements_dir) if file.startswith("def_")]

    # print("existing_files:", existing_files)

    # 既存のファイル名と被らないようにファイル名を生成するプロンプトを作成
    file_name_prompt = f"{prompt}に基づいて、要件定義書のファイル名をdef_hogehoge.mdの形式で提案してください。\n"
    file_name_prompt += f"ただし、以下の既存のファイル名と被らないようにしてください。\n{', '.join(existing_files)}\n"
    file_name_prompt += "ファイル名のみを1つだけアウトプットしてください。\n"
    file_name_prompt += "単一のファイル名以外は絶対に出力しないでください\n"
    # print("file_name_prompt:", file_name_prompt)
    response = litellm.generate_response(settings.model_name_smart, file_name_prompt, 100, 0.7)
    file_name = response.strip()

    # 複数ファイル名が取れるケースがあるのでsplitして１つ目だけ取る
    file_names = file_name.split("\n")
    if len(file_names) > 1:
        file_name = file_names[0]

    # 禁止文字を削除
    ng_word = ["\\", "/", ":", "*", "?", '"', "<", ">", "|", " "]
    for word in ng_word:
        file_name = file_name.replace(word, "")
    return f"{file_name}"
