import os
import sys

from tqdm import tqdm

from zoltraak.converter.base_converter import BaseConverter
from zoltraak.core.prompt_manager import PromptManager
from zoltraak.schema.schema import MagicInfo, MagicLayer, SourceTargetSet
from zoltraak.utils.file_util import FileUtil
from zoltraak.utils.log_util import log, log_inout


class FileAnalyzer(BaseConverter):
    """LLMの出力結果が保存されたファイルとファイル構成を解析するクラス
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
            MagicLayer.LAYER_2_1_AFFECTED_FILE_LIST_GEN,
        ]
        self.name = "FileAnalyzer"

    @log_inout
    def prepare_generation(self) -> list[SourceTargetSet]:
        """
        解析の準備を行うメソッド
        """
        # step1: ファイル情報を更新
        self.source_target_set_list = []
        file_info = self.magic_info.file_info

        # affected_file_list
        affected_file_list = FileUtil.read_affected_file_list_content(
            file_info.request_file_path, file_info.target_dir, file_info.canonical_name
        )

        for code_file_path in tqdm(affected_file_list, unit="files", file=sys.stdout, desc="prepare_analyze"):
            source_target_set = self.prepare_generation_file(code_file_path)
            if source_target_set:
                self.source_target_set_list.append(source_target_set)
                log("append source_target_set= %s", source_target_set)

        return self.source_target_set_list

    @log_inout
    def prepare_generation_file(self, code_file_path: str) -> SourceTargetSet | None:
        # code_file_path: structure_file由来の最終的に生成するべきファイルパス(拡張子はpy or mdを想定)

        # requirement_file_path: ソースファイルに対する変更要求のファイルパス
        requirement_file_path = os.path.splitext(code_file_path)[0] + "_requirement.md"

        # file_info.request_file_path: 要求定義書（全体）
        request_file_path = self.magic_info.file_info.request_file_path
        request_file_content = FileUtil.read_file(request_file_path)

        # info_structure_file_path: 個々の詳細設計書に対応する情報構造体のファイルパス
        requirement_file_content = FileUtil.read_file(requirement_file_path)
        requirement_file_content += "\n\n更新要求がありました。\n\n"
        requirement_file_content += request_file_content
        FileUtil.write_file(requirement_file_path, requirement_file_content)

        if self.magic_info.magic_layer is MagicLayer.LAYER_2_1_AFFECTED_FILE_LIST_GEN:
            # MagicLayer.LAYER_2_1_AFFECTED_FILE_LIST_GEN
            # 変更要求 => 要求定義書（ファイル別）
            source_file_path = request_file_path
            target_file_path = requirement_file_path
            context_file_path = ""
        else:
            # 呼ばれないはず
            source_file_path = ""
            target_file_path = ""
            context_file_path = ""

        return SourceTargetSet(
            source_file_path=source_file_path, target_file_path=target_file_path, context_file_path=context_file_path
        )

    def convert(self) -> str:
        """詳細設計書 => ソースファイル"""
        # 変換処理の実体なし（TODO: 例外処理で何かするかも）
        return self.magic_info.file_info.target_file_path


if __name__ == "__main__":  # このスクリプトが直接実行された場合にのみ、以下のコードを実行します。
    magic_info_ = MagicInfo()
    prompt_manager_ = PromptManager()
    converter = FileAnalyzer(magic_info_, prompt_manager_)
    converter.convert()
