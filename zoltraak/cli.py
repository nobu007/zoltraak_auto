import argparse
import os
import os.path
import sys

import zoltraak
import zoltraak.llms.litellm_api as litellm
from zoltraak import settings
from zoltraak.converter.converter import MarkdownToPythonConverter
from zoltraak.converter.md_converter import MarkdownToMarkdownConverter
from zoltraak.schema.schema import MagicInfo, MagicLayer, MagicMode, ZoltraakParams
from zoltraak.utils.file_util import FileUtil
from zoltraak.utils.log_util import log
from zoltraak.utils.rich_console import display_info_full, display_magic_info_final, display_magic_info_full
from zoltraak.utils.subprocess_util import SubprocessUtil


def main():
    """メイン処理"""
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
        default=str(MagicLayer.LAYER_2_REQUIREMENT_GEN),
    )
    args = parser.parse_args()
    if args.version:  # バージョン情報表示オプションが指定された場合
        show_version_and_exit()  # - バージョン情報を表示して終了

    if args.input is None:  # 入力ファイルまたはテキストが指定されていない場合
        show_usage_and_exit()  # - 使用方法を表示して終了

    if args.model_name:  # -- 使用するモデルの名前が指定された場合
        settings.model_name = args.model_name  # -- zoltraak全体設定に保存してどこからでも使えるようにする

    # compiler_path確定
    compiler_path = prepare_compiler(args.input, args.compiler, args.custom_compiler)

    params = ZoltraakParams()
    params.input = args.input
    params.prompt = args.prompt
    params.compiler = compiler_path  # compilerとcustom_compilerを集約(絶対パス)
    params.formatter = args.formatter
    params.language = args.language
    params.model_name = args.model_name
    params.magic_mode = args.magic_mode
    params.magic_layer = args.magic_layer
    log("params.input=" + params.input)
    if params.input.endswith(".md"):
        params.canonical_name = os.path.basename(params.input)
        # 初回になければ作成対象のファイルを生成する
        first_md_file_path = os.path.abspath(params.input)
        if not os.path.isfile(first_md_file_path):
            FileUtil.write_file(first_md_file_path, "")
    display_info_full(params, title="ZoltraakParams")

    if params.input.endswith(".md"):
        # (暫定) inputで要件定義書.mdを指定されたらメイン処理実行
        magic_info = process_markdown_file(params)
        display_magic_info_final(magic_info)
    else:
        # inputでテキストを指定されたらテキスト入力処理
        zoltraak_command = process_text_input(params)  # - テキスト入力を処理する関数を呼び出す
        log("zoltraak_command=" + zoltraak_command)  # - 実行したzoltraakコマンドを表示 (デバッグ用)

    # llm使用量を表示
    litellm.show_used_total_tokens()


def prepare_compiler(input_: str, compiler: str, custom_compiler: str) -> str:
    if compiler and custom_compiler:  # -- デフォルトのコンパイラーとカスタムコンパイラーの両方が指定されている場合
        show_compiler_conflict_error_and_exit()  # --- コンパイラー競合エラーを表示して終了

    # compilerが有効かチェック
    valid_compiler = get_valid_compiler(compiler)
    if valid_compiler:
        return valid_compiler

    # custom_compilerが有効かチェック
    valid_compiler = get_valid_compiler(custom_compiler)
    if valid_compiler:
        return valid_compiler

    # inputで指定されたcompilerが有効かチェック
    valid_compiler = get_valid_compiler(input_)
    if valid_compiler:
        return valid_compiler

    # inputでcompilerが指定されているかチェック
    valid_compiler = get_valid_compiler(compiler)
    if valid_compiler:
        return valid_compiler

    # どれも無効な場合はデフォルトコンパイラを返す
    return get_valid_compiler("dev_obj")


def get_valid_compiler(compiler_candidate: str) -> str:
    """有効なcompilerだったらその絶対パスを返す
    無効なら空文字を返す"""
    return get_valid_markdown(compiler_candidate, settings.compiler_dir)


def get_valid_formatter(compiler_candidate: str) -> str:
    """有効なformatterだったらその絶対パスを返す
    無効なら空文字を返す"""
    return get_valid_markdown(compiler_candidate, settings.formatter_dir)


def get_valid_markdown(markdown_candidate: str, additional_dir: str = "") -> str:
    """有効だったらその絶対パスを返す
    無効なら空文字を返す"""
    if not markdown_candidate:
        log("空文字")
        return ""

    # 拡張子".md"を準備して、以降はファイル存在チェックする
    if not markdown_candidate.endswith(".md"):
        markdown_candidate += ".md"

    # カレントディレクトリをチェック(絶対パスで来た場合もここで返す)
    candidate_abs = os.path.abspath(markdown_candidate)
    if os.path.isfile(candidate_abs):
        log("検出 " + candidate_abs)
        return candidate_abs

    # additional_dir配下をチェック
    if additional_dir:
        candidate_abs = os.path.join(additional_dir, markdown_candidate)
        if os.path.isfile(candidate_abs):
            log("検出(additional_dir配下) " + candidate_abs)
            return candidate_abs

    log("無効 " + markdown_candidate)
    return ""


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


def process_markdown_file(params: ZoltraakParams) -> MagicInfo:
    """
    Markdownファイルを処理する
    前提： params.input で処理対象のmarkdownファイルが指定される
    """
    compiler_path_abs = os.path.abspath(params.compiler)
    output_dir_abs = os.path.abspath(params.output_dir)

    formatter_path = get_valid_formatter(params.formatter)

    canonical_name = params.canonical_name
    md_file_path = params.input  # この時点では新規ファイルの可能性があるので、get_valid_markdown()はNG
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
    magic_info.prompt = params.prompt
    magic_info.current_grimoire_name = canonical_name
    magic_info.description = ""  # デフォルト値を使う
    magic_info.grimoire_compiler = compiler_path_abs
    magic_info.grimoire_architect = ""  # 後で設定する
    magic_info.grimoire_formatter = formatter_path

    # file関連
    magic_info.file_info.md_file_path = md_file_path
    magic_info.file_info.py_file_path = py_file_path
    magic_info.file_info.update()
    magic_info.file_info.canonical_name = canonical_name
    magic_info.file_info.target_dir = output_dir_abs

    # その他
    magic_info.success_message = ""  # 後で設定する
    magic_info.error_message = ""  # 後で設定する
    magic_info.language = params.language
    magic_info.is_debug = False
    display_magic_info_full(magic_info)

    mtp = create_converter(magic_info)
    os.makedirs(
        os.path.dirname(py_file_path), exist_ok=True
    )  # Pythonファイルの出力ディレクトリを作成（既に存在する場合は何もしない）
    new_file_path = mtp.convert_loop()
    magic_info.file_info.final_output_file_path = new_file_path
    return magic_info


# TO_MARKDOWN_CONVERTER を使うレイヤの一覧
TO_MARKDOWN_CONVERTER_LAYER_LIST = ["layer_1_request_gen", "2_requirement_gen"]


def create_converter(magic_info: MagicInfo):
    log("magic_info.magic_layer=%s", magic_info.magic_layer)
    if magic_info.magic_layer in TO_MARKDOWN_CONVERTER_LAYER_LIST:
        # マークダウンに変換するコンバータを使う
        log("MarkdownToMarkdownConverter")
        return MarkdownToMarkdownConverter(magic_info)
    # pythonに変換するコンバータを使う
    log("MarkdownToPythonConverter")
    return MarkdownToPythonConverter(magic_info)


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
