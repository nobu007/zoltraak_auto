import os

from zoltraak.converter.base_converter import BaseConverter
from zoltraak.schema.schema import MagicInfo, MagicLayer
from zoltraak.utils.file_util import FileUtil
from zoltraak.utils.log_util import log_inout


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

    def __init__(self, magic_info: MagicInfo):
        self.magic_info = magic_info

    @log_inout
    def convert(self) -> str:
        """prompt + ユーザ要求記述書(pre_md_file) => 要件定義書(md_file)"""

        # step1: ファイル情報を更新
        file_info = self.magic_info.file_info
        file_info.update_path_abs()

        # step2: ユーザ要求記述書を作成(TODO: ここで実際に変換すると一気に要件定義書まで作れる)
        if self.magic_info.magic_layer is MagicLayer.LAYER_1_REQUEST_GEN:
            file_info.update_source_target(file_info.prompt_file_path_abs, file_info.pre_md_file_path_abs)
            file_info.update_hash()

        # step3: 要件定義書を作成(TODO: ここで実際に変換すると一気に要件定義書まで作れる)
        if self.magic_info.magic_layer is MagicLayer.LAYER_2_REQUIREMENT_GEN:
            file_info.update_source_target(file_info.pre_md_file_path_abs, file_info.md_file_path_abs)
            file_info.update_hash()

        # step4: 変換処理
        new_file_path = self.convert_one()
        new_file_path_abs = os.path.abspath(new_file_path)
        target_file_path_abs = os.path.abspath(file_info.target_file_path)
        if new_file_path_abs != target_file_path_abs:
            # copy to file_info.target_file_path
            return FileUtil.copy_file(new_file_path, target_file_path_abs)
        return target_file_path_abs


if __name__ == "__main__":  # このスクリプトが直接実行された場合にのみ、以下のコードを実行します。
    magic_info_ = MagicInfo()

    # レイヤ１
    magic_info_.magic_layer = MagicLayer.LAYER_1_REQUEST_GEN
    converter = MarkdownToMarkdownConverter(magic_info_)
    converter.convert()

    # レイヤ２
    magic_info_.magic_layer = MagicLayer.LAYER_2_REQUIREMENT_GEN
    converter = MarkdownToMarkdownConverter(magic_info_)
    converter.convert()