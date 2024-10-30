import os
import sys

from tqdm import tqdm

from zoltraak.converter.base_converter import BaseConverter
from zoltraak.core.prompt_manager import PromptManager
from zoltraak.schema.schema import MagicInfo, MagicLayer, SourceTargetSet
from zoltraak.utils.file_util import FileUtil
from zoltraak.utils.log_util import log, log_inout


class FileRemover(BaseConverter):
    """ファイル構造定義書から、不要ファイルを削除する
    前提:
      MagicInfo.FileInfoに入出力ファイルが展開済み
        md_file_path: 要件定義書
        structure_file_path: ファイル構造定義書
    """

    def __init__(self, magic_info: MagicInfo, prompt_manager: PromptManager):
        super().__init__(magic_info, prompt_manager)
        self.magic_info = magic_info
        self.prompt_manager = prompt_manager
        self.acceptable_layers = [
            MagicLayer.LAYER_9_CLEAN_UP,
        ]
        self.name = "FileRemover"

    @log_inout
    def prepare_generation(self) -> list[SourceTargetSet]:
        """
        ターゲットコードベース生成の準備を行うメソッド
        """
        # step1: ファイル構造定義書を取得
        file_info = self.magic_info.file_info
        code_file_path_list = FileUtil.read_structure_file_content(
            file_info.structure_file_path, file_info.target_dir, file_info.canonical_name
        )
        code_file_path_final_list = FileUtil.read_structure_file_content(
            file_info.structure_file_path, file_info.final_dir, file_info.canonical_name
        )

        # step2: ファイルリストとファイル構造定義書を比較して、不要ファイルを削除
        removed_file_paths_set = self.remove_dirs(file_info.target_dir, code_file_path_list)
        removed_dir_paths_set = self.remove_dirs(file_info.final_dir, code_file_path_final_list)
        return removed_file_paths_set + removed_dir_paths_set

    @log_inout
    def remove_dirs(self, root_dir: str, code_file_path_list: list[str]) -> list[str]:
        """指定フォルダ配下をルールに従って削除する"""

        # ファイル,フォルダリストを取得
        file_paths, dir_paths = FileUtil.find_files(root_dir, "")  # 拡張子が空文字列の場合は全ファイルを取得

        # ファイルリストとファイル構造定義書を比較して、不要ファイルを削除
        self.magic_info.history_info += " ->クリーンアップ(対象なしでスキップ)"
        remove_count = 0
        removed_file_paths_set = []
        for file_path in tqdm(file_paths, file=sys.stdout):
            log("check file_path= %s", file_path)
            if FileRemover.should_remove_file(file_path, code_file_path_list):
                log("remove file_path= %s", file_path)
                os.remove(file_path)
                remove_count += 1
                self.magic_info.history_info = f"クリーンアップ(削除ファイル数: {remove_count})"

                # 無駄な処理が発生するので追加しない
                # removed_file_paths_set.append(SourceTargetSet(source_file_path=file_path, target_file_path=file_path))

        # step4: フォルダリストから空フォルダを削除
        for dir_path in sorted(dir_paths, reverse=True):  # 末端から削除するためソート
            if not os.listdir(dir_path):
                log("remove dir_path= %s", dir_path)
                os.rmdir(dir_path)  # noqa: PTH106, TH106

        return removed_file_paths_set

    @staticmethod
    def should_remove_file(file_path: str, code_file_path_list: list[str]):
        """削除対象かどうかを判定する

        条件： どのコードファイルにも対応していないファイルは削除対象
        対応とはコードファイルの拡張子を除いた文字列が含まれること

        例：code_file_path_list=["./src/main.py", "./src/utils/file_util.py"]
        file_path="./src/__init__.py" は削除対象
        file_path="./src/main.py" は削除対象ではない
        file_path="./src/main.md" は削除対象ではない
        file_path="./src/utils/file_util_test.py" は削除対象ではない
        file_path="./utils/file_util.py" は削除対象
        """
        # ただし、次の例外ワードを含むファイルは削除しない
        not_remove_word_list = ["info_structure.md"]
        for not_remove_word in not_remove_word_list:
            if not_remove_word in file_path:
                return False

        # 削除判定メイン処理
        for code_file_path in code_file_path_list:  # noqa: SIM110
            code_file_path_without_ext = os.path.splitext(code_file_path)[0]
            if code_file_path_without_ext in file_path:
                return False
        return True

    @log_inout
    def convert(self) -> str:
        """削除のみなので処理なし"""
        return self.magic_info.file_info.target_file_path


if __name__ == "__main__":  # このスクリプトが直接実行された場合にのみ、以下のコードを実行します。
    magic_info_ = MagicInfo()
    prompt_manager_ = PromptManager()
    converter = FileRemover(magic_info_, prompt_manager_)
    converter.prepare_generation()
