import os

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
            MagicLayer.LAYER_8_CLEAN_UP,
        ]
        self.name = "FileRemover"

    @log_inout
    def prepare_generation(self) -> list[SourceTargetSet]:
        """
        ターゲットコードベース生成の準備を行うメソッド
        """
        # step1: ファイル構造定義書を取得
        file_info = self.magic_info.file_info
        code_file_path_list = FileUtil.read_structure_file_content(file_info.structure_file_path, file_info.target_dir)

        # step2: ファイルリストを取得
        file_paths = FileUtil.find_files(file_info.target_dir, "")  # 拡張子が空文字列の場合は全ファイルを取得

        # step3: ファイルリストとファイル構造定義書を比較して、不要ファイルを削除
        for file_path in file_paths:
            log("check file_path= %s", file_path)
            if file_path not in code_file_path_list:
                log("remove file_path= %s", file_path)
                os.remove(file_path)

        return []


if __name__ == "__main__":  # このスクリプトが直接実行された場合にのみ、以下のコードを実行します。
    magic_info_ = MagicInfo()
    prompt_manager_ = PromptManager()
    converter = FileRemover(magic_info_, prompt_manager_)
    converter.prepare_generation()
