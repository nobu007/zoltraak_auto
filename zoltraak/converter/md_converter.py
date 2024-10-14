from zoltraak.converter.base_converter import BaseConverter
from zoltraak.core.prompt_manager import PromptManager
from zoltraak.schema.schema import MagicInfo, MagicLayer
from zoltraak.utils.log_util import log, log_inout


class MarkdownToMarkdownConverter(BaseConverter):
    """マークダウンを更新するコンバーター
    前提:
      MagicInfoにモードとレイヤーが展開済み
        MagicMode
        MagicLayer
      MagicInfo.FileInfoに入出力ファイルが展開済み
        prompt_file_path
        request_file_path
        structure_file_path
        md_file_path
        py_file_path

    MagicLayer によってsourceとtargetファイルが変化する
    どのレイヤーでもsourceのマークダウンにはtargetへの要求が書かれている。
    この処理はsourceの要求をtargetのマークダウンに反映することである。

    <LAYER_1>
      source => prompt_file_path
      target => request_file_path
    <LAYER_2>
      source => prompt_file_path
      target => structure_file_path
    <LAYER_3(not active)>
    """

    def __init__(self, magic_info: MagicInfo, prompt_manager: PromptManager):
        super().__init__(magic_info, prompt_manager)
        self.magic_info = magic_info
        self.prompt_manager = prompt_manager
        self.acceptable_layers = [
            MagicLayer.LAYER_1_REQUEST_GEN,
            MagicLayer.LAYER_2_REQUIREMENT_GEN,
            MagicLayer.LAYER_3_REQUIREMENT_GEN,
        ]

    @log_inout
    def convert(self) -> str:
        """prompt + ユーザ要求記述書(pre_md_file) => 要件定義書(md_file)"""

        # step1: ファイル情報を更新
        file_info = self.magic_info.file_info

        # step2: ユーザ要求記述書を作成
        if self.magic_info.magic_layer is MagicLayer.LAYER_1_REQUEST_GEN:
            self.magic_info.grimoire_compiler = "general_prompt.md"
            log("レイヤ1専用のプロンプト: %s", self.magic_info.grimoire_compiler)
            file_info.update_source_target(file_info.prompt_file_path, file_info.request_file_path)
            file_info.update_hash()

        # step3: ファイル構造定義書を作成
        if self.magic_info.magic_layer is MagicLayer.LAYER_2_REQUIREMENT_GEN:
            self.magic_info.grimoire_compiler = "structure_full.md"
            log("レイヤ2専用のプロンプト: %s", self.magic_info.grimoire_compiler)
            file_info.update_source_target(file_info.prompt_file_path, file_info.structure_file_path)
            file_info.update_hash()

        # step4: 要件定義書を作成
        if self.magic_info.magic_layer is MagicLayer.LAYER_3_REQUIREMENT_GEN:
            self.magic_info.grimoire_compiler = "dev_obj.md"
            log("レイヤ3専用のプロンプト: %s", self.magic_info.grimoire_compiler)
            file_info.update_source_target(file_info.request_file_path, file_info.md_file_path)
            file_info.update_hash()

        # step5: 変換処理
        return self.convert_one()


if __name__ == "__main__":  # このスクリプトが直接実行された場合にのみ、以下のコードを実行します。
    magic_info_ = MagicInfo()
    prompt_manager_ = PromptManager()

    # レイヤ１
    magic_info_.magic_layer = MagicLayer.LAYER_1_REQUEST_GEN
    converter_ = MarkdownToMarkdownConverter(magic_info_, prompt_manager_)
    converter_.convert()

    # レイヤ３
    magic_info_.magic_layer = MagicLayer.LAYER_3_REQUIREMENT_GEN
    converter = MarkdownToMarkdownConverter(magic_info_, prompt_manager_)
    converter.convert()
