import os
import re
import sys
import time

import zoltraak.llms.litellm_api as litellm
from zoltraak import settings
from zoltraak.schema.schema import MagicInfo
from zoltraak.utils.file_util import FileUtil
from zoltraak.utils.log_util import log, log_e
from zoltraak.utils.rich_console import generate_response_with_spinner


def generate_md_from_prompt_recursive(magic_info: MagicInfo) -> str:
    file_info = magic_info.file_info
    """
    promptから要件定義書（マークダウンファイル）を生成する関数
    """
    compiler_path = magic_info.get_compiler_path()
    formatter_path = magic_info.get_formatter_path()
    language = magic_info.language

    # プロンプトコンパイラとプロンプトフォーマッタを変数として受け取る
    if (
        compiler_path is not None and "grimoires" in compiler_path
    ):  # grimoires/ディレクトリにコンパイラパスが含まれている場合
        prompt_compiler = os.path.basename(
            compiler_path
        )  # - コンパイラパスからファイル名のみを取得してprompt_compilerに代入
    else:  # grimoires/ディレクトリにコンパイラパスが含まれていない場合
        prompt_compiler = compiler_path  # - コンパイラパスをそのままprompt_compilerに代入

    prompt_formatter = get_prompt_formatter(language, formatter_path)
    prompt_final = create_prompt(magic_info.prompt, compiler_path, formatter_path, language)  # プロンプトを作成
    magic_info.current_grimoire_name = prompt_compiler
    magic_info.grimoire_formatter = prompt_formatter
    magic_info.description = "ステップ1. \033[31m起動術式\033[0mを用いて\033[32m魔法術式\033[0mを構築"
    magic_info.prompt_final = prompt_final
    file_info.canonical_name = os.path.basename(file_info.target_file_path)
    file_info.target_file_path = f"requirements/{file_info.canonical_name}"
    response = generate_response_with_spinner(magic_info, prompt_final)
    md_content = response.strip()  # 生成された要件定義書の内容を取得し、前後の空白を削除
    output_file_path = save_md_content(
        md_content, file_info.target_file_path
    )  # 生成された要件定義書の内容をファイルに保存
    file_info.add_output_file_path(output_file_path)

    # 重要： オリジナルの target_file_path にコピーする
    output_file_path_abs = os.path.abspath(output_file_path)
    target_file_path_abs = os.path.abspath(file_info.target_file_path)
    if output_file_path_abs != target_file_path_abs:
        # copy to file_info.target_file_path
        os.makedirs(os.path.dirname(output_file_path_abs), exist_ok=True)
        return FileUtil.copy_file(output_file_path_abs, target_file_path_abs)

    # 重要： ここで target_file_path をrequirement配下に置き換える
    file_info.update_source_target(file_info.source_file_path, output_file_path)
    file_info.update()

    print_generation_result(file_info.target_file_path)  # 生成結果を出力
    return output_file_path


def get_prompt_formatter(language: str, formatter_path: str):
    # 汎用言語フォーマッタへの変更
    if language:
        # grimoire_formatter に_lang.mdが存在するならそれを、しないならformatter_pathのまま
        lang_formatter_path = os.path.splitext(formatter_path)[0] + "_lang.md"
        if os.path.exists(lang_formatter_path):
            formatter_path = lang_formatter_path

    # フォーマッターについて、デフォフォルダの時見栄えをシンプルにする
    if "grimoires" in formatter_path:  # grimoires/ディレクトリにフォーマッタパスが含まれている場合  # noqa: SIM108
        prompt_formatter = os.path.basename(
            formatter_path
        )  # - フォーマッタパスからファイル名のみを取得してprompt_formatterに代入
    else:  # grimoires/ディレクトリにフォーマッタパスが含まれていない場合
        prompt_formatter = formatter_path  # - フォーマッタパスをそのままprompt_formatterに代入
    return prompt_formatter


def show_spinner(done, goal):
    """スピナーを表示する関数

    Args:
        done (function): スピナーを終了するかどうかを判定する関数
    """
    progress_bar = "━" * 22

    spinner_base = goal + "中... 🪄 "
    spinner_animation = [
        f"{progress_bar[:i]}☆ﾟ.*･｡ﾟ{' ' * (len(progress_bar) - i)}" for i in range(1, len(progress_bar) + 1)
    ] + [f"{progress_bar}☆ﾟ.*･｡"]
    spinner = [spinner_base + anim for anim in spinner_animation]

    while not done():  # done()がFalseの間、スピナーを表示し続ける
        for cursor in spinner:  # - スピナーのアニメーションパターンを順番に処理
            sys.stdout.write(
                cursor + "\b" * (len(cursor) + 100)
            )  # -- カーソル文字を出力し、その文字数分だけバックスペースを出力して上書き
            sys.stdout.flush()  # -- 出力をフラッシュして即時表示
            time.sleep(0.1)  # -- 0.1秒のディレイを追加


def generate_response(developer, model_name, prompt):  # noqa: ARG001
    """
    対応デベロッパーごとに分岐してレスポンスを生成する関数

    現在対応しているデベロッパーとモデルは以下の通りです:
    - Anthropic:
      - claude-3-opus-20240229
      - claude-3-sonnet-20240229
      - claude-3-haiku-20240307
    - Groq:
      - llama3-8b-8192
      - llama3-70b-8192
      - llama2-70b-4096
      - mixtral-8x7b-32768
      - gemma-7b-it

    Args:
        prompt (str): APIに送信するプロンプト

    Returns:
        str: APIから生成されたレスポンス
    """
    return litellm.generate_response(model_name, prompt, 4000, 0.7)


def create_prompt(goal_prompt, compiler_path=None, formatter_path=None, language=None):
    """
    LLMへのプロンプトを作成する関数

    Args:
        goal_prompt (str): 要件定義書の生成に使用するプロンプト
        compiler_path (str): コンパイラのパス
        formatter_path (str): フォーマッタのパス

    Returns:
        str: 作成されたプロンプト
    """
    # prompt_file = "grimoires/compiler/dev_obj.md"  # デフォルトのプロンプトファイルのパスを指定
    # if compiler_path:  # コンパイラパスが指定されている場合
    # prompt_file = compiler_path  # - プロンプトファイルのパスをコンパイラパスに変更

    formatter = get_formatter(formatter_path, language)

    if compiler_path is None:
        # 検索関数の起動
        compiler_dir = settings.compiler_dir
        compiler_files = [file for file in os.listdir(compiler_dir) if file.endswith(".md")]

        prompt = "以下のファイルから、goal_promptに最も適したものを選んでください。\n\n"

        for file in compiler_files:
            file_path = os.path.join(compiler_dir, file)
            with open(file_path, encoding="utf-8") as f:
                content = f.read().split("\n")[:3]
            prompt += f"## {file}\n```\n{' '.join(content)}\n```\n\n"

        prompt += f"## goal_prompt\n\n```{goal_prompt}```\n\n"
        prompt += f"""まず、goal_promptを踏まえて、最初に取るべきステップを明示してください。
        そのステップやgoal_prompt自身と比較して、最も適切なファイルを上位5つ選び、それぞれの理由とともに説明してください。
        また、それぞれの実行プロンプトを、zoltraak \"{goal_prompt}\" -c [ファイル名（拡張子なし）]で、code blockに入れて添付してください。"""  # noqa: E501
        prompt += prompt + formatter
    elif os.path.exists(compiler_path):  # プロンプトファイルが存在する場合
        with open(compiler_path, encoding="utf-8") as file:  # - プロンプトファイルを読み込みモードで開く
            prompt = file.read().format(
                prompt=goal_prompt
            )  # -- プロンプトファイルの内容を読み込み、goal_promptを埋め込む
        prompt = prompt + formatter  # - プロンプトにフォーマッタを追加
    else:  # プロンプトファイルが存在しない場合
        log_e(f"プロンプトファイル {compiler_path} が見つかりません。")  # - エラーメッセージを表示
        os.system("pwd")  # noqa: S605, S607
        prompt = ""

    if prompt != "" and language is not None:
        if not formatter_path.endswith("_lang.md"):
            try:
                start_index = formatter.rindex("## Output Language")
                prompt = (
                    formatter[start_index:]
                    + "\n- Follow the format defined in the format section. DO NOT output the section itself."
                    + prompt
                )  # 言語指定の強調前出しでサンドイッチにしてみる。
            except ValueError:
                # rindexが取れなかった場合の処理
                prompt = (
                    "\n- Follow the format defined in the format section. DO NOT output the section itself." + prompt
                )

        elif re.match("(english|英語|en)", language.lower()):
            prompt = (
                formatter + prompt
            )  # 特に英語指示が「デフォルト言語指示」と混同されやすく、効きがやたら悪いので英語の場合は挟み撃ちにする

    # print(prompt) # デバッグ用
    return prompt


def get_formatter(formatter_path, language=None):
    """
    フォーマッタを取得する関数

    Args:
        formatter_path (str): フォーマッタのパス

    Returns:
        str: フォーマッタの内容
    """
    if formatter_path is None:  # フォーマッタパスが指定されていない場合
        formatter = ""  # - フォーマッタを空文字列に設定
    elif os.path.exists(formatter_path):  # -- フォーマッタファイルが存在する場合
        with open(formatter_path, encoding="utf-8") as file:  # --- フォーマッタファイルを読み込みモードで開く
            formatter = file.read()  # ---- フォーマッタの内容を読み込む
            if language is not None:
                if formatter_path.endswith("_lang.md"):
                    formatter = formatter.replace("{language}", language)
                else:
                    formatter += f"\n- You must output everything including code block and diagrams, according to the previous instructions, but make sure you write your response in {language}.\n\n## Output Language\n- You must generate your response using {language}, which is the language of the formatter just above this sentence."  # noqa: E501
    else:  # -- フォーマッタファイルが存在しない場合
        log_e(f"フォーマッタファイル {formatter_path} が見つかりません。")  # --- エラーメッセージを表示
        formatter = ""  # --- フォーマッタを空文字列に設定

    return formatter


def save_md_content(md_content, target_file_path) -> str:
    """
    生成された要件定義書の内容をファイルに保存する関数

    Args:
        md_content (str): 生成された要件定義書の内容
        target_file_path (str): 保存先のファイルパス
    """
    requirements_dir = "requirements"  # 生成された要件定義書をrequirements/の中に格納する
    os.makedirs(requirements_dir, exist_ok=True)  # - requirements/ディレクトリを作成（既に存在する場合は何もしない）
    target_file_name = os.path.basename(target_file_path)  # - ターゲットファイルのファイル名を取得
    target_file_path = os.path.join(
        requirements_dir, target_file_name
    )  # - requirements/ディレクトリとファイル名を結合してターゲットファイルのパスを生成
    with open(target_file_path, "w", encoding="utf-8") as target_file:  # ターゲットファイルを書き込みモードで開く
        target_file.write(md_content)  # - 生成された要件定義書の内容をファイルに書き込む
        return target_file_path
    return ""


def print_generation_result(target_file_path):
    """
    要件定義書の生成結果を表示する関数

    Args:
        target_file_path (str): 生成された要件定義書のファイルパス
    """
    print()
    log(f"\033[32m魔法術式を構築しました: {target_file_path}\033[0m")  # 要件定義書の生成完了メッセージを緑色で表示
