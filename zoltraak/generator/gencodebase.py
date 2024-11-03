import os
import sys

from tqdm import tqdm

from zoltraak.converter.base_converter import BaseConverter
from zoltraak.core.prompt_manager import PromptManager
from zoltraak.schema.schema import MagicInfo, MagicLayer, SourceTargetSet
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
            MagicLayer.LAYER_7_INFO_STRUCTURE_GEN,
            MagicLayer.LAYER_8_INFO_STRUCTURE_GEN,
            MagicLayer.LAYER_9_CODE_GEN,
        ]
        self.name = "CodeBaseGenerator"

    @log_inout
    def prepare_generation(self) -> list[SourceTargetSet]:
        """
        ターゲットコードベース生成の準備を行うメソッド
        """
        # step1: ファイル情報を更新
        file_info = self.magic_info.file_info
        code_file_path_list = FileUtil.read_structure_file_content(
            file_info.structure_file_path, file_info.target_dir, file_info.canonical_name
        )

        for code_file_path in tqdm(
            code_file_path_list, unit="files", file=sys.stdout, desc=self.magic_info.magic_layer
        ):
            if os.path.isfile(code_file_path):
                source_target_set = self.prepare_generation_code_file(code_file_path)
                self.source_target_set_list.append(source_target_set)
                log("append source_target_set= %s", source_target_set)

        # コンテキストには
        # step2: グリモア更新
        # 変更なし

        # step3: プロンプト更新
        self.magic_info.prompt_input = ""

        return self.source_target_set_list

    @log_inout
    def prepare_generation_code_file(self, code_file_path: str) -> SourceTargetSet:
        # target_file_path(生成済の個々のソースファイルに対応する詳細設計書)
        code_base_file_path = os.path.splitext(code_file_path)[0] + ".md"  # .mdに変更
        if code_base_file_path == code_file_path:
            code_base_file_path += ".md"  # もともと.mdだった場合は.md.mdになる

        # info_structure_file_path(情報構造体)
        info_structure_file_path = os.path.join(os.path.dirname(code_file_path), "info_structure.md")

        if self.magic_info.magic_layer is MagicLayer.LAYER_6_CODEBASE_GEN:
            # MagicLayer.LAYER_6_CODEBASE_GEN
            # ソースファイル => 詳細設計書
            source_file_path = code_file_path
            target_file_path = code_base_file_path
            context_file_path = self.magic_info.file_info.request_file_path
            self.magic_info.grimoire_compiler = "dev_obj_file.md"
        elif self.magic_info.magic_layer is MagicLayer.LAYER_7_INFO_STRUCTURE_GEN:
            # MagicLayer.LAYER_7_INFO_STRUCTURE_GEN
            # 詳細設計書 => 情報構造体要素
            source_file_path = code_base_file_path
            target_file_path = code_base_file_path + "_info_structure.md"
            context_file_path = info_structure_file_path
            self.magic_info.grimoire_compiler = "dev_info_structure.md"
        elif self.magic_info.magic_layer is MagicLayer.LAYER_8_INFO_STRUCTURE_GEN:
            # MagicLayer.LAYER_8_INFO_STRUCTURE_GEN
            # 情報構造体要素 => 情報構造体
            source_file_path = code_base_file_path + "_info_structure.md"
            target_file_path = info_structure_file_path
            context_file_path = self.magic_info.file_info.request_file_path
            self.magic_info.grimoire_compiler = "dev_info_structure_final.md"
        elif self.magic_info.magic_layer is MagicLayer.LAYER_9_CODE_GEN:
            # MagicLayer.LAYER_9_CODE_GEN
            # 情報構造体 => 最終コード（再作成）
            code_file_path_rel = os.path.relpath(code_file_path, self.magic_info.file_info.target_dir)
            code_file_path_final = os.path.join(self.magic_info.file_info.final_dir, code_file_path_rel)
            source_file_path = code_base_file_path
            target_file_path = code_file_path_final
            context_file_path = info_structure_file_path
            self.magic_info.grimoire_compiler = "dev_obj_final.md"
        else:
            # 呼ばれないはず
            source_file_path = ""
            target_file_path = ""
            context_file_path = ""

        return SourceTargetSet(
            source_file_path=source_file_path, target_file_path=target_file_path, context_file_path=context_file_path
        )

    def convert(self) -> str:
        """コード => コードベース"""
        return self.convert_one()

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
