import os
import sys

from tqdm import tqdm

from zoltraak.converter.base_converter import BaseConverter
from zoltraak.core.prompt_manager import PromptManager
from zoltraak.schema.schema import MagicInfo, MagicLayer, SourceTargetSet
from zoltraak.utils.file_util import FileUtil
from zoltraak.utils.log_util import log, log_inout


class CodeGenerator(BaseConverter):
    """ディレクトリとファイル構成から、コードを作るファイル
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
            MagicLayer.LAYER_4_REQUIREMENT_GEN,
            MagicLayer.LAYER_5_CODE_GEN,
        ]
        self.name = "CodeGenerator"

    @log_inout
    def prepare_generation(self) -> list[SourceTargetSet]:
        """
        コード生成の準備を行うメソッド
        """
        # step1: ファイル情報を更新
        self.source_target_set_list = []
        file_info = self.magic_info.file_info
        code_file_path_list = FileUtil.read_structure_file_content(
            file_info.structure_file_path, file_info.target_dir, file_info.canonical_name
        )
        print("code_file_path_list=", len(code_file_path_list))

        for code_file_path in tqdm(
            code_file_path_list,
            unit="files",
            file=sys.stdout,
            desc=self.magic_info.magic_layer + "(prepare_generation)",
        ):
            source_target_set = self.prepare_generation_code_file(code_file_path)
            if source_target_set:
                file_extension = os.path.splitext(source_target_set.target_file_path)[1]
                if file_extension != "":
                    # 拡張子なしのファイルはスキップ
                    self.source_target_set_list.append(source_target_set)
                    log("append source_target_set= %s", source_target_set)

        # コンテキストには
        # step2: グリモア更新
        # 変更なし

        # step3: プロンプト更新
        self.magic_info.prompt_input = ""

        return self.source_target_set_list

    @log_inout
    def prepare_generation_code_file(self, code_file_path: str) -> SourceTargetSet | None:
        # code_file_path: structure_file由来の最終的に生成するべきファイルパス(拡張子はpy or mdを想定)

        # code_base_file_path: 生成済の個々のソースファイルに対応する詳細設計書のファイルパス
        code_base_file_path = os.path.splitext(code_file_path)[0] + ".md"  # .mdに変更
        if code_base_file_path == code_file_path:
            code_base_file_path += ".md"  # もともと.mdだった場合は.md.mdになる

        # requirement_file_path: ソースファイルに対する変更要求のファイルパス
        requirement_file_path = os.path.splitext(code_file_path)[0] + "_requirement.md"

        # info_structure_file_path: 個々の詳細設計書に対応する情報構造体のファイルパス
        info_structure_file_path = os.path.splitext(code_file_path)[0] + "_info_structure.md"
        # info_structure_file_path_merged: ディレクトリ単位で集約した情報構造体のファイルパス
        info_structure_file_path_merged = os.path.join(os.path.dirname(code_file_path), "info_structure.md")
        log("info_structure_file_path_merged=%s", info_structure_file_path_merged)

        context_file_path = ""
        if self.magic_info.magic_layer is MagicLayer.LAYER_4_REQUIREMENT_GEN:
            # MagicLayer.LAYER_4_REQUIREMENT_GEN
            # 要件定義書 => 要求定義書（ファイル別）
            source_file_path = self.magic_info.file_info.md_file_path
            target_file_path = requirement_file_path
            context_file_path = ""
            self.magic_info.grimoire_compiler = "dev_request_python.md"
        elif self.magic_info.magic_layer is MagicLayer.LAYER_5_CODE_GEN:
            # MagicLayer.LAYER_5_CODE_GEN
            # 詳細設計書 => ソースファイル
            source_file_path = requirement_file_path
            target_file_path = code_file_path
            context_file_path = info_structure_file_path
            if target_file_path.endswith(".py"):
                self.magic_info.grimoire_compiler = "dev_code_python.md"
            else:
                # mdの場合を想定（README.mdなど）
                self.magic_info.grimoire_compiler = "general_md.md"
        else:
            # 呼ばれないはず
            source_file_path = ""
            target_file_path = ""
            context_file_path = ""

        return SourceTargetSet(
            source_file_path=source_file_path, target_file_path=target_file_path, context_file_path=context_file_path
        )

    def convert(self) -> float:
        """詳細設計書 => ソースファイル"""
        return self.convert_one()

    @log_inout
    def convert_one(self) -> float:
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
    converter = CodeGenerator(magic_info_, prompt_manager_)
    converter.convert()
