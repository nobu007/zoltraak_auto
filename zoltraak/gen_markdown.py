from zoltraak.utils.file_util import FileUtil
from zoltraak.utils.log_util import log
from zoltraak.utils.rich_console import MagicInfo, generate_response_with_spinner


def generate_md_from_prompt(magic_info: MagicInfo) -> str:
    """
    prompt_finalから任意のマークダウンファイルを生成する関数
    """
    response = generate_response_with_spinner(magic_info, magic_info.prompt_final)
    target_file_path = magic_info.file_info.target_file_path
    md_content = response.strip()  # 生成された要件定義書の内容を取得し、前後の空白を削除
    output_file_path = save_md_content(md_content, target_file_path)  # 生成された要件定義書の内容をファイルに保存
    print_generation_result(output_file_path)  # 生成結果を出力
    return output_file_path


def save_md_content(md_content, target_file_path) -> str:
    """
    生成された要件定義書の内容をファイルに保存する関数

    Args:
        md_content (str): 生成された要件定義書の内容
        target_file_path (str): 保存先のファイルパス
    """
    return FileUtil.write_grimoire(md_content, target_file_path)


def print_generation_result(output_file_path):
    """
    要件定義書の生成結果を表示する関数

    Args:
        output_file_path (str): 生成された要件定義書のファイルパス
    """
    print()
    log(f"\033[32m魔法術式を構築しました: {output_file_path}\033[0m")  # 要件定義書の生成完了メッセージを緑色で表示


if __name__ == "__main__":  # このスクリプトが直接実行された場合にのみ、以下のコードを実行します。
    magic_info_ = MagicInfo()
    magic_info_.file_info.update()
    generate_md_from_prompt(magic_info_)
