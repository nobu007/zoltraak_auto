import os

from zoltraak.utils.log_util import log


class FileUtil:
    @staticmethod
    def read_file(file_path: str) -> str:
        # ターゲットファイルの現在の内容を読み込む
        with open(file_path, encoding="utf-8") as file:
            return file.read()
        return f"{file_path} を開けませんでした。"

    @staticmethod
    def write_file(file_path: str, content: str) -> str:
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(content)
            return file_path
        return ""

    @staticmethod
    def read_grimoire(file_path: str, prompt: str = "", language: str = "") -> str:
        # グリモアをpromptとlanguageをreplaceして読み込む
        content = FileUtil.read_file(file_path)
        content = content.replace("{prompt}", prompt)
        content = content.replace("{language}", language)
        log(f"read_grimoire content:\n {content}")
        return content

    @staticmethod
    def write_grimoire(md_content: str, file_path_abs: str) -> str:
        os.makedirs(os.dirname(file_path_abs), exist_ok=True)
        FileUtil.write_file(file_path_abs, md_content)
