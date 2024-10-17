from zoltraak.utils.file_util import FileUtil
from zoltraak.utils.rich_console import MagicInfo, generate_response_with_spinner


def generate_md_from_prompt(magic_info: MagicInfo) -> str:
    """
    prompt_finalから任意のマークダウンファイルを生成する関数
    """
    response = generate_response_with_spinner(magic_info, magic_info.prompt_final)
    target_file_path = magic_info.file_info.target_file_path

    md_content = response.strip()  # 生成された要件定義書の内容を取得し、前後の空白を削除
    return save_md_content(md_content, target_file_path)  # 生成された要件定義書の内容をファイルに保存


def save_md_content(md_content, target_file_path) -> str:
    """
    生成された要件定義書の内容をファイルに保存する関数

    Args:
        md_content (str): 生成された要件定義書の内容
        target_file_path (str): 保存先のファイルパス
    """
    return FileUtil.write_grimoire(md_content, target_file_path)


if __name__ == "__main__":  # このスクリプトが直接実行された場合にのみ、以下のコードを実行します。
    magic_info_ = MagicInfo()
    magic_info_.file_info.update()
    generate_md_from_prompt(magic_info_)
