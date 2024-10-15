import os

from zoltraak.converter.base_converter import BaseConverter
from zoltraak.core.prompt_manager import PromptManager
from zoltraak.schema.schema import MagicInfo, MagicLayer
from zoltraak.utils.file_util import FileUtil
from zoltraak.utils.log_util import log, log_inout


class CodeBaseGenerator(BaseConverter):
    """ディレクトリとファイル構成から、コードベースを作るファイル
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
            MagicLayer.LAYER_6_CODEBASE_GEN,
            MagicLayer.LAYER_7_REQUIREMENT_GEN,
        ]
        self.name = "CodeBaseGenerator"
        self.source_file_path_list = []

    @log_inout
    def prepare_generation(self):
        """
        ターゲットコードベース生成の準備を行うメソッド
        """
        # step1: ファイル情報を更新
        file_info = self.magic_info.file_info
        structure_file_path = file_info.structure_file_path
        structure_file_content = FileUtil.read_file(structure_file_path)

        for file_path_rel in structure_file_content.split("\n"):
            log("file_path_rel=%s", file_path_rel)
            file_path = os.path.abspath(os.path.join(file_info.target_dir, file_path_rel))
            if os.path.isfile(file_path):
                self.source_file_path_list.append(file_path)

        return self.source_file_path_list

    def convert(self) -> str:
        """コード => コードベース"""
        self.convert_one()

    @log_inout
    def convert_one(self) -> str:
        """生成処理を１回実行する"""
        file_info = self.magic_info.file_info

        # ターゲットファイルの有無による分岐
        if FileUtil.has_content(file_info.target_file_path):  # ターゲットファイルが存在する場合
            return self.handle_existing_target_file()  # - 既存のターゲットファイルを処理
        # ターゲットファイルが存在しない場合
        return self.handle_new_target_file()  # - 新しいターゲットファイルを処理


if __name__ == "__main__":  # このスクリプトが直接実行された場合にのみ、以下のコードを実行します。
    magic_info_ = MagicInfo()
    prompt_manager_ = PromptManager()
    converter = CodeBaseGenerator(magic_info_, prompt_manager_)
    converter.convert()
