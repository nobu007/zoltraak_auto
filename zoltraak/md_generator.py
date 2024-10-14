import os
import sys
import time

from zoltraak.schema.schema import MagicInfo
from zoltraak.utils.log_util import log
from zoltraak.utils.rich_console import generate_response_with_spinner


def generate_md_from_prompt_recursive(magic_info: MagicInfo) -> str:
    file_info = magic_info.file_info
    """
    promptから要件定義書（マークダウンファイル）を生成する関数
    """
    magic_info.description = "ステップ1. \033[31m起動術式\033[0mを用いて\033[32m魔法術式\033[0mを構築"
    response = generate_response_with_spinner(magic_info, magic_info.prompt_final)
    md_content = response.strip()  # 生成された要件定義書の内容を取得し、前後の空白を削除
    output_file_path = save_md_content(
        md_content, file_info.target_file_path
    )  # 生成された要件定義書の内容をファイルに保存

    print_generation_result(output_file_path)  # 生成結果を出力
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


# def create_prompt(goal_prompt, compiler_path=None, formatter_path=None, language=None):
#     """
#     LLMへのプロンプトを作成する関数

#     Args:
#         goal_prompt (str): 要件定義書の生成に使用するプロンプト
#         compiler_path (str): コンパイラのパス
#         formatter_path (str): フォーマッタのパス

#     Returns:
#         str: 作成されたプロンプト
#     """
#     # prompt_file = "grimoires/compiler/dev_obj.md"  # デフォルトのプロンプトファイルのパスを指定
#     # if compiler_path:  # コンパイラパスが指定されている場合
#     # prompt_file = compiler_path  # - プロンプトファイルのパスをコンパイラパスに変更

#     formatter = get_formatter(formatter_path, language)

#     if compiler_path is None:
#         # 検索関数の起動
#         compiler_dir = settings.compiler_dir
#         compiler_files = [file for file in os.listdir(compiler_dir) if file.endswith(".md")]

#         prompt = "以下のファイルから、goal_promptに最も適したものを選んでください。\n\n"

#         for file in compiler_files:
#             file_path = os.path.join(compiler_dir, file)
#             with open(file_path, encoding="utf-8") as f:
#                 content = f.read().split("\n")[:3]
#             prompt += f"## {file}\n```\n{' '.join(content)}\n```\n\n"

#         prompt += f"## goal_prompt\n\n```{goal_prompt}```\n\n"
#         prompt += f"""まず、goal_promptを踏まえて、最初に取るべきステップを明示してください。
#         そのステップやgoal_prompt自身と比較して、最も適切なファイルを上位5つ選び、それぞれの理由とともに説明してください。# noqa: E501
#         また、それぞれの実行プロンプトを、zoltraak \"{goal_prompt}\" -c [ファイル名（拡張子なし）]で、code blockに入れて添付してください。"""  # noqa: E501
#         prompt += prompt + formatter
#     elif os.path.exists(compiler_path):  # プロンプトファイルが存在する場合
#         with open(compiler_path, encoding="utf-8") as file:  # - プロンプトファイルを読み込みモードで開く
#             prompt = file.read().format(
#                 prompt=goal_prompt
#             )  # -- プロンプトファイルの内容を読み込み、goal_promptを埋め込む
#         prompt = prompt + formatter  # - プロンプトにフォーマッタを追加
#     else:  # プロンプトファイルが存在しない場合
#         log_e(f"プロンプトファイル {compiler_path} が見つかりません。")  # - エラーメッセージを表示
#         os.system("pwd")  # noqa: S605, S607
#         prompt = ""

#     if prompt != "" and language is not None:
#         if not formatter_path.endswith("_lang.md"):
#             try:
#                 start_index = formatter.rindex("## Output Language")
#                 prompt = (
#                     formatter[start_index:]
#                     + "\n- Follow the format defined in the format section. DO NOT output the section itself."
#                     + prompt
#                 )  # 言語指定の強調前出しでサンドイッチにしてみる。
#             except ValueError:
#                 # rindexが取れなかった場合の処理
#                 prompt = (
#                     "\n- Follow the format defined in the format section. DO NOT output the section itself." + prompt
#                 )

#         elif re.match("(english|英語|en)", language.lower()):
#             prompt = (
#                 formatter + prompt
#             )  # 特に英語指示が「デフォルト言語指示」と混同されやすく、効きがやたら悪いので英語の場合は挟み撃ちにする

#     # print(prompt) # デバッグ用
#     return prompt


def save_md_content(md_content, target_file_path) -> str:
    """
    生成された要件定義書の内容をファイルに保存する関数

    Args:
        md_content (str): 生成された要件定義書の内容
        target_file_path (str): 保存先のファイルパス
    """
    with open(target_file_path, "w", encoding="utf-8") as output_file:  # ターゲットファイルを書き込みモードで開く
        output_file.write(md_content)  # - 生成された要件定義書の内容をファイルに書き込む
        return target_file_path
    return ""


def print_generation_result(output_file_path):
    """
    要件定義書の生成結果を表示する関数

    Args:
        output_file_path (str): 生成された要件定義書のファイルパス
    """
    print()
    log(f"\033[32m魔法術式を構築しました: {output_file_path}\033[0m")  # 要件定義書の生成完了メッセージを緑色で表示
