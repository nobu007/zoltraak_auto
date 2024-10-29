import os
import pathlib
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
        replace_map: dict[str, str] | None = None,
    ) -> str:
        # グリモアをpromptとlanguageとcontextをreplaceして読み込む
        content = FileUtil.read_file(file_path)
        content = content.replace("{prompt}", prompt)
        content = content.replace("{language}", language)
        content = content.replace("{requirements_content}", requirements_content)
        content = content.replace("{source_content}", source_content)
        content = content.replace("{target_content}", target_content)

        # 変数を置換する
        if replace_map:
            for key, value in replace_map.items():
                content = content.replace(f"[{key}]", value)
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
    def read_structure_file_content(structure_file_path: str, target_dir: str, canonical_name: str) -> list[str]:
        """
        構造ファイルの内容を読み込み、絶対ファイルパスのリストを返します。

        引数:
            structure_file_path: 相対ファイルパスを含む構造ファイルのパス。
            target_dir: 相対ファイルパスを解決するためのターゲットディレクトリ。
            canonical_name: アウトプットファイルやフォルダを一意に識別するための正規名称

        戻り値:
            list[str]: ターゲットディレクトリに存在する絶対ファイルパスのリスト。
        """
        structure_file_content = FileUtil.read_file(structure_file_path)
        file_path_list = []
        for file_path_rel in structure_file_content.split("\n"):
            log("check file_path_rel= %s", file_path_rel)
            file_path = os.path.abspath(os.path.join(target_dir, canonical_name, file_path_rel))
            if os.path.isfile(file_path):
                file_path_list.append(file_path)
                log("append file_path= %s", file_path)
            else:
                log("not exist= %s", file_path)
        return file_path_list

    @staticmethod
    def copy_file(src_file_path: str, dis_file_path: str) -> str:
        return shutil.copy(src_file_path, dis_file_path)

    THRESHOLD_BYTES_MIN_CONTENT = 100  # ファイル内にコンテンツありと見なす閾値

    @staticmethod
    def has_content(file_path: str, threshold: int = THRESHOLD_BYTES_MIN_CONTENT) -> bool:
        content = FileUtil.read_file(file_path)
        log("file_path= %s, content(len)= %d", file_path, len(content))
        return len(content) > threshold

    @staticmethod
    def log_file_content(file_path: str):
        if settings.is_debug:
            file_content = FileUtil.read_file(file_path)
            log_i("=" * 80)
            log_i("%s content=%s", file_path, file_content)
            log_i("=" * 80)

    @staticmethod
    def find_files(root_path: str, ext: str = ".py") -> tuple[list[str], list[str]]:
        """Find files in the root_path

        Args:
            root_path (str): root path to find files

        Returns:
            list[str]: list of file paths
        """
        file_paths = []
        dir_paths = []
        if os.path.isdir(root_path):  # noqa: PTH112
            for path in pathlib.Path(root_path).glob(f"**/*{ext}"):
                if path.is_file():
                    log(path)
                    file_paths.append(str(path.resolve()))
                elif path.is_dir():
                    dir_paths.append(str(path.resolve()))

        return file_paths, dir_paths
