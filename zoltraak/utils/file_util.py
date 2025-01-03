import datetime
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
        # TODO: PromptManager版に置き換える
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
        # TODO: PromptManagerに移動する
        # TODO: 何かグリモアに特化した前処理などを追加する
        FileUtil.write_file(file_path_abs, md_content)
        return file_path_abs

    @staticmethod
    def write_prompt(md_content: str, file_path_abs: str) -> str:
        # 空のコンテンツは書かない
        if md_content:
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
    def read_structure_file_content(structure_file_path: str, base_dir: str, canonical_name: str) -> list[str]:
        """
        構造ファイルの内容を読み込み、絶対ファイルパスのリストを返します。

        引数:
            structure_file_path: 相対ファイルパスを含む構造ファイルのパス。
            base_dir: 絶対パスに変換するときのベースディレクトリ。
            canonical_name: アウトプットファイルやフォルダを一意に識別するための正規名称

        戻り値:
            list[str]: ベースディレクトリに配置されるファイルの絶対パスのリスト。
        """
        structure_file_content = FileUtil.read_file(structure_file_path)
        file_path_list = []
        for file_path_rel in structure_file_content.split("\n"):
            log("check file_path_rel= %s", file_path_rel)
            file_path = os.path.abspath(os.path.join(base_dir, file_path_rel))
            if canonical_name not in file_path:
                # canonical_nameが入ってない場合は付与
                file_path = os.path.abspath(os.path.join(base_dir, canonical_name, file_path_rel))
            if "```" not in file_path:
                # plaintxtの囲み部分でなければ採用（チェック時に存在しなくても登録が必要）
                file_path_list.append(file_path)
                log("append file_path= %s", file_path)
        return file_path_list

    @staticmethod
    def read_affected_file_list_content(request_file_path: str, base_dir: str, canonical_name: str) -> list[str]:
        """
        ユーザ要求記述書の内容を読み込み、修正対象のファイルパスのリストを返します。

        引数:
            request_file_path: ユーザ要求記述書のファイルパス。
            base_dir: 絶対パスに変換するときのベースディレクトリ。
            canonical_name: アウトプットファイルやフォルダを一意に識別するための正規名称

        戻り値:
            list[str]: ベースディレクトリに配置されるファイルの絶対パスのリスト。
        """
        request_file_content = FileUtil.read_file(request_file_path)

        def get_file_path(line: str) -> str:
            file_path_rel = line.strip()
            file_path_rel = re.sub("^- ", "", file_path_rel)  # 先頭の"-"と" "を削除
            file_path = os.path.abspath(os.path.join(base_dir, file_path_rel))
            if canonical_name not in file_path:
                file_path = os.path.abspath(os.path.join(base_dir, canonical_name, file_path_rel))
            if os.path.isfile(file_path):
                log("file found file_path= %s", file_path)
                return file_path
            log("file not found: %s", file_path)
            return None

        # request_file_contentから"### 修正対象のファイルパス"に続くファイルパスを取得
        file_path_list = []
        is_capturing = False
        for line in request_file_content.split("\n"):
            if "### 修正対象のファイルパス" in line:
                is_capturing = True
                continue
            if is_capturing:
                file_path = get_file_path(line)
                if file_path:
                    file_path_list.append(file_path)
                    log("append file_path= %s", file_path)
                continue
            if is_capturing and "###" in line:
                # 他のセクションに入ったら終了
                is_capturing = False
                break

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

    @staticmethod
    def get_timestamp(file_path: str) -> datetime.datetime:
        """ファイルのタイムスタンプを取得します"""
        if os.path.isfile(file_path):
            timestamp = pathlib.Path(file_path).stat().st_mtime
            return datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)  # noqa: UP017
        # ファイルが存在しない場合は1970年1月1日に設定
        return datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc)  # noqa: UP017
