import os
import re
import shutil

from zoltraak import settings
from zoltraak.utils.log_util import log, log_i


class FileUtil:
    @staticmethod
    def read_file(file_path: str) -> str:
        if os.path.isfile(file_path):
            with open(file_path, encoding="utf-8") as file:
                lines = [line.rstrip() for line in file.readlines()]
                return "\n".join(lines)
        return ""

    @staticmethod
    def write_file(file_path: str, content: str) -> str:
        if not file_path:
            return "ファイルパスが空です。"
        if not content:
            return "ファイルの内容が空です。"

        file_dir = os.path.dirname(file_path)
        if file_dir != "" and not os.path.exists(file_dir):
            try:
                os.makedirs(file_dir, exist_ok=True)
            except OSError as e:
                log(f"ディレクトリの作成に失敗しました: {e}")
                return f"ディレクトリの作成に失敗しました: {e}"
        try:
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(content)
                return file_path
        except OSError as e:
            log(f"ファイルの書き込みに失敗しました: {e}")
            return f"ファイルの書き込みに失敗しました: {e}"

    @staticmethod
    def read_grimoire(
        file_path: str,
        prompt: str = "",
        language: str = "",
        requirements_content: str = "",
        source_content: str = "",
        target_content: str = "",
    ) -> str:
        # グリモアをpromptとlanguageとcontextをreplaceして読み込む
        content = FileUtil.read_file(file_path)
        content = content.replace("{prompt}", prompt)
        content = content.replace("{language}", language)
        content = content.replace("{requirements_content}", requirements_content)
        content = content.replace("{source_content}", source_content)
        content = content.replace("{target_content}", target_content)
        log(f"read_grimoire content[:100]:\n {content[:100]}")
        return content

    @staticmethod
    def write_grimoire(md_content: str, file_path_abs: str) -> str:
        # TODO: 何かグリモアに特化した前処理などを追加する
        FileUtil.write_file(file_path_abs, md_content)
        return file_path_abs

    @staticmethod
    def read_md_recursive(file_path: str) -> str:
        """mdファイルを再帰的に読み込む"""
        log("file_path=%s", file_path)
        if os.path.isfile(file_path):
            contents = FileUtil.read_file(file_path)
            # contentsにxx.mdが含まれていたら再帰的に読み込む
            md_links = re.findall(r"\[.*?\]\((.*?)\)", contents)
            log("md_links=%s", md_links)
            for md_link in md_links:
                if md_link.endswith(".md"):
                    linked_file_path = os.path.abspath(os.path.join(os.path.dirname(file_path), md_link))
                    contents += f"\n\n{md_link}\n" + FileUtil.read_md_recursive(linked_file_path)
            return contents
        return ""

    @staticmethod
    def copy_file(src_file_path: str, dis_file_path: str) -> str:
        return shutil.copy(src_file_path, dis_file_path)

    THRESHOLD_BYTES_MIN_CONTENT = 100  # ファイル内にコンテンツありと見なす閾値

    @staticmethod
    def has_content(file_path: str, threshold: int = THRESHOLD_BYTES_MIN_CONTENT) -> bool:
        content = FileUtil.read_file(file_path)
        log_i("has_content file_path= %s, content(len)= %d", file_path, len(content))
        return len(content) > threshold

    @staticmethod
    def log_file_content(file_path: str):
        if settings.is_debug:
            file_content = FileUtil.read_file(file_path)
            log_i("=" * 80)
            log_i("%s content=%s", file_path, file_content)
            log_i("=" * 80)
