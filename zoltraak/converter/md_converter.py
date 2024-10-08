from zoltraak.converter.base_converter import BaseConverter
from zoltraak.converter.converter import MarkdownToPythonConverter
from zoltraak.core.magic_workflow import MagicWorkflow
from zoltraak.schema.schema import MagicLayer
from zoltraak.utils.log_util import log, log_inout


class MarkdownToMarkdownConverter(BaseConverter):
    """マークダウンを更新するコンバーター
    前提:
      MagicInfoにモードとレイヤーが展開済み
        MagicMode
        MagicLayer
      MagicInfo.FileInfoに入出力ファイルが展開済み
        prompt_file_path
        pre_md_file_path
        md_file_path
        py_file_path

    MagicLayer によってsourceとtargetファイルが変化する
    どのレイヤーでもsourceのマークダウンにはtargetへの要求が書かれている。
    この処理はsourceの要求をtargetのマークダウンに反映することである。

    <LAYER_1>
      source => prompt_file_path
      target => pre_md_file_path
    <LAYER_2>
      source => pre_md_file_path
      target => md_file_path
    <LAYER_3(not active)>
      source => md_file_path
      target => py_file_path
    """

    def __init__(self, magic_workflow: MagicWorkflow):
        super().__init__(magic_workflow)
        self.magic_workflow = magic_workflow
        self.magic_info = magic_workflow.magic_info

    @log_inout
    def convert_loop(self) -> str:
        """convert処理をレイヤを進めながら繰り返す"""

        # MarkdownToMarkdownConverter loop
        acceptable_layers = [MagicLayer.LAYER_1_REQUEST_GEN, MagicLayer.LAYER_2_REQUIREMENT_GEN]
        output_file_path = self.magic_workflow.run_loop(self.convert, acceptable_layers)
        log("output_file_path=%s", output_file_path)

        # MarkdownToPythonConverter
        py_converter = MarkdownToPythonConverter(self.magic_workflow)
        output_file_path_final = py_converter.convert_loop()
        log("output_file_path_final=%s", output_file_path_final)

        return output_file_path_final

    @log_inout
    def convert(self) -> str:
        """prompt + ユーザ要求記述書(pre_md_file) => 要件定義書(md_file)"""

        # step1: ファイル情報を更新
        file_info = self.magic_info.file_info
        file_info.update_path_abs()

        # step2: ユーザ要求記述書を作成
        if self.magic_info.magic_layer is MagicLayer.LAYER_1_REQUEST_GEN:
            file_info.update_source_target(file_info.prompt_file_path_abs, file_info.pre_md_file_path_abs)
            file_info.update_hash()

        # step3: 要件定義書を作成
        if self.magic_info.magic_layer is MagicLayer.LAYER_2_REQUIREMENT_GEN:
            file_info.update_source_target(file_info.pre_md_file_path_abs, file_info.md_file_path_abs)
            file_info.update_hash()

        # step4: 変換処理
        return self.magic_workflow.run(self.convert_one)


if __name__ == "__main__":  # このスクリプトが直接実行された場合にのみ、以下のコードを実行します。
    magic_workflow = MagicWorkflow()

    # レイヤ１
    magic_workflow.magic_info.magic_layer = MagicLayer.LAYER_1_REQUEST_GEN
    converter = MarkdownToMarkdownConverter(magic_workflow)
    converter.convert()

    # レイヤ３
    magic_workflow.magic_info.magic_layer = MagicLayer.LAYER_3_REQUIREMENT_GEN
    converter = MarkdownToMarkdownConverter(magic_workflow)
    converter.convert()
