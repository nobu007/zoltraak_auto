import os
import re

from zoltraak.utils.file_util import FileUtil
from zoltraak.utils.log_util import log, log_e
from zoltraak.utils.rich_console import MagicInfo, generate_response_with_spinner


def generate_md_from_prompt(magic_info: MagicInfo) -> str:
    file_info = magic_info.file_info
    """
    promptから任意のマークダウンファイルを生成する関数
    利用するグリモアはMagicInfoに展開済みの前提

    設計：
        利用するグリモアとプロンプトは上位処理で設定済みなので、
        ここではプロンプトを作成し、それを利用してマークダウンファイルを生成する。
        プロンプトにはsourceとtargetのファイルコンテンツ情報も反映済みである。

    """
    compiler_path = magic_info.get_compiler_path()
    formatter_path = magic_info.get_formatter_path()
    language = magic_info.language

    prompt = create_prompt(magic_info.prompt, compiler_path, formatter_path, language)  # プロンプトを作成
    magic_info.prompt = prompt
    response = generate_response_with_spinner(magic_info)
    md_content = response.strip()  # 生成された要件定義書の内容を取得し、前後の空白を削除
    return save_md_content(md_content, file_info.target_file_path)  # 生成された要件定義書の内容をファイルに保存


def create_prompt(goal_prompt: str, compiler_path: str, formatter_path: str, language: str):
    """
    LLMへのプロンプトを作成する関数

    Returns:
        str: 作成されたプロンプト
    """

    prompt = goal_prompt
    if os.path.isfile(compiler_path):
        # コンパイラが存在する場合、コンパイラベースでプロンプトを取得
        prompt = FileUtil.read_grimoire(compiler_path, goal_prompt, language)
        prompt += "\n\n"
    if os.path.exists(formatter_path):
        prompt = modify_prompt(prompt, formatter_path, language)
    return prompt


def modify_prompt(final_prompt: str, formatter_path: str, language: str):
    modified_prompt = final_prompt
    if formatter_path != "" and language is not None:
        formatter_prompt = get_formatter_prompt(formatter_path, language)
        # 多言語のフォーマッターの場合、言語指定を強調する
        if not formatter_path.endswith("_lang.md"):
            try:
                find_word = "## Output Language"
                start_index = final_prompt.rindex(find_word)
                end_index = start_index + len(find_word) + 1  # TODO: もっと正確に探す
                modified_prompt = (
                    final_prompt[:start_index]
                    + "\n- Follow the format defined in the format section. DO NOT output the section itself."
                    + formatter_prompt
                    + final_prompt[end_index:]
                )  # 言語指定の強調前出しでサンドイッチにしてみる。
            except ValueError:
                # rindexが取れなかった場合の処理
                final_prompt = (
                    "\n- Follow the format defined in the format section. DO NOT output the section itself."
                    + final_prompt
                )

        elif re.match("(english|英語|en)", language.lower()):
            modified_prompt = (
                final_prompt + formatter_prompt
            )  # 特に英語指示が「デフォルト言語指示」と混同されやすく、効きがやたら悪いので英語の場合は挟み撃ちにする
    log("modified_prompt[:100]=" + modified_prompt[:100])
    return modified_prompt


def get_formatter_prompt(formatter_path: str, language: str | None = None):
    """
    フォーマッタを取得する関数

    Args:
        formatter_path (str): フォーマッタのパス

    Returns:
        str: フォーマッタの内容
    """
    if formatter_path is None:  # フォーマッタパスが指定されていない場合
        formatter_prompt = ""  # - フォーマッタを空文字列に設定
    elif os.path.exists(formatter_path):  # -- フォーマッタファイルが存在する場合
        formatter_prompt = FileUtil.read_grimoire(formatter_path, language=language)
        if language and formatter_path.endswith("_lang.md"):
            formatter_prompt += f"""\n- You must output everything including code block and diagrams,
            according to the previous instructions, but make sure you write your response in {language}.

            \n## Output Language\n- You must generate your response using {language},
            which is the language of the formatter just above this sentence."""
    else:  # -- フォーマッタファイルが存在しない場合
        log_e(f"フォーマッタファイル {formatter_path} が見つかりません。")  # --- エラーメッセージを表示
        formatter_prompt = ""  # --- フォーマッタを空文字列に設定

    return formatter_prompt


def save_md_content(md_content, target_file_path) -> str:
    """
    生成された要件定義書の内容をファイルに保存する関数

    Args:
        md_content (str): 生成された要件定義書の内容
        target_file_path (str): 保存先のファイルパス
    """
    requirements_dir = "requirements"  # 生成された要件定義書をrequirements/の中に格納する
    target_file_name = os.path.basename(target_file_path)  # - ターゲットファイルのファイル名を取得
    target_file_path = os.path.join(
        requirements_dir, target_file_name
    )  # - requirements/ディレクトリとファイル名を結合してターゲットファイルのパスを生成
    return FileUtil.write_grimoire(md_content, target_file_path)


if __name__ == "__main__":  # このスクリプトが直接実行された場合にのみ、以下のコードを実行します。
    magic_info_ = MagicInfo()
    magic_info_.file_info.update()
    generate_md_from_prompt(magic_info_)
