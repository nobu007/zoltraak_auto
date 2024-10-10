import os
import shutil

from zoltraak.utils.log_util import log, log_i


class FileUtil:
    @staticmethod
    # def read_file(file_path: str) -> str:
    #     # ターゲットファイルの現在の内容を読み込む
    #     if os.path.isfile(file_path):
    #         with open(file_path, encoding="utf-8") as file:
    #             return "\n".join(file.readlines())
    #     return f"{file_path} を開けませんでした。"
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
    def read_grimoire(file_path: str, prompt: str = "", language: str = "") -> str:
        # グリモアをpromptとlanguageをreplaceして読み込む
        content = FileUtil.read_file(file_path)
        content = content.replace("{prompt}", prompt)
        content = content.replace("{language}", language)
        log(f"read_grimoire content[:100]:\n {content[:100]}")
        return content

    @staticmethod
    def write_grimoire(md_content: str, file_path_abs: str) -> str:
        # TODO: 何かグリモアに特化した前処理などを追加する
        FileUtil.write_file(file_path_abs, md_content)
        return file_path_abs

    @staticmethod
    def copy_file(src_file_path: str, dis_file_path: str) -> str:
        return shutil.copy(src_file_path, dis_file_path)

    THRESHOLD_BYTES_MIN_CONTENT = 500  # ファイル内にコンテンツありと見なす閾値

    @staticmethod
    def has_content(file_path: str, threshold: int = THRESHOLD_BYTES_MIN_CONTENT) -> bool:
        content = FileUtil.read_file(file_path)
        log_i("has_content file_path= %s, content(len)= %d", file_path, len(content))
        return len(content) > threshold
