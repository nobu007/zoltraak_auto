import os

import zoltraak.llms.litellm_api as litellm
from zoltraak import settings
from zoltraak.converter.base_converter import BaseConverter
from zoltraak.core.magic_workflow import MagicWorkflow
from zoltraak.gencode import TargetCodeGenerator
from zoltraak.md_generator import generate_md_from_prompt_recursive
from zoltraak.schema.schema import MagicLayer
from zoltraak.utils.file_util import FileUtil
from zoltraak.utils.log_util import log, log_e, log_inout, log_w
from zoltraak.utils.rich_console import display_magic_info_intermediate
from zoltraak.utils.subprocess_util import SubprocessUtil


class MarkdownToPythonConverter(BaseConverter):
    """マークダウン(要件定義書)からpythonコードを更新するコンバーター
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
    この処理はsourceの要求をtarget(マークダウン or Pythonコード)に反映することである。

    <LAYER_0(not active)>
      source => prompt_file_path
      target => pre_md_file_path
    <LAYER_1(not active)>
      source => pre_md_file_path
      target => md_file_path
    <LAYER_2>
      source => md_file_path
      target => md_file_path
    <LAYER_3>
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
        acceptable_layers = [MagicLayer.LAYER_3_REQUIREMENT_GEN, MagicLayer.LAYER_4_CODE_GEN]
        for layer in MagicLayer:
            log("check layer = " + str(layer))
            if layer in acceptable_layers and layer == self.magic_info.magic_layer:
                log("convert layer = " + str(layer))
                self.magic_info.file_info.final_output_file_path = self.convert()
                display_magic_info_intermediate(self.magic_info)
                self.magic_info.magic_layer = layer.next()  # --- 次のレイヤに進む
                log("end next = " + str(self.magic_info.magic_layer))
        return self.magic_info.file_info.final_output_file_path

    @log_inout
    def convert(self) -> str:
        """要件定義書(md_file) => Pythonコード"""

        # step1: ファイル情報を更新
        file_info = self.magic_info.file_info
        file_info.update_path_abs()

        # step2: 要件定義書を更新
        if self.magic_info.magic_layer is MagicLayer.LAYER_3_REQUIREMENT_GEN:
            file_info.update_source_target(file_info.md_file_path_abs, file_info.md_file_path_abs)
            file_info.update_hash()

            return self.magic_workflow.run(self.convert_one_md_md)

        # step3: Pythonコードを作成
        if self.magic_info.magic_layer is MagicLayer.LAYER_4_CODE_GEN:
            file_info.update_source_target(file_info.md_file_path_abs, file_info.py_file_path_abs)
            file_info.update_hash()

            return self.magic_workflow.run(self.convert_one_md_py)

        return ""

    @log_inout
    def convert_one_md_md(self) -> str:
        """要件定義書(md_file) => 要件定義書(md_file)の１ファイルを変換する"""

        file_info = self.magic_info.file_info
        if FileUtil.has_content(file_info.target_file_path):  # -- マークダウンファイルのコンテンツが有効な場合
            log(
                f"{file_info.target_file_path}は既存のファイルです。promptに従って変更を提案します。"
            )  # --- ファイルが既存であることを示すメッセージを表示
            self.propose_target_diff(
                file_info.target_file_path, self.magic_info.prompt
            )  # --- プロンプトに従ってターゲットファイルの差分を提案

            return file_info.target_file_path  # --- 関数を終了
        # --- マークダウンファイルのコンテンツが無効な場合
        return self.handle_new_target_file_md()  # --- 新しいターゲットファイルを処理

    @log_inout
    def convert_one_md_py(self) -> str:
        """要件定義書(md_file) => my or pyの１ファイルを変換する"""
        if FileUtil.has_content(self.magic_info.file_info.target_file_path):
            return self.handle_existing_target_file_py()
        return self.handle_new_target_file_py()

    @log_inout
    def handle_existing_target_file_py(self) -> str:
        file_info = self.magic_info.file_info
        with open(file_info.target_file_path, encoding="utf-8") as target_file:
            lines = target_file.readlines()
            if len(lines) > 0 and lines[-1].startswith("# HASH: "):
                embedded_hash = lines[-1].split("# HASH: ")[1].strip()
                log("embedded_hash=%s", embedded_hash)
                log("source_hash=%s", file_info.source_hash)
                log("prompt=%s", self.magic_info.prompt)
                if file_info.source_hash == embedded_hash:
                    if not self.magic_info.prompt:
                        # TODO: targetがpyなら別プロセスで実行の方が良い？
                        # 現状はプロンプトが無い => ユーザ要求がtarget に全て反映済みなら次ステップに進む設計
                        # targetのpastとの差分が一定未満なら次に進むでもいいかも。
                        SubprocessUtil.run(
                            ["python", file_info.target_file_path, "-ml", self.magic_info.magic_layer], check=False
                        )
                        return file_info.target_file_path  # TODO: サブプロセスで作った別ファイルの情報は不要？
                    # target に埋め込まれたハッシュがsource (最新)に一致してたらスキップ
                    # TODO: ハッシュ運用検討
                    # source が同じでもコンパイラやプロンプトの更新でtarget が変わる可能性もある？
                    # どこかにtarget のinput全部を詰め込んだハッシュが必要？
                    return file_info.target_file_path

                # file_info.source_hash != embedded_hash
                # source が変わってたらtarget を作り直す
                # TODO: 前回のtarget を加味したほうが良い？
                # =>source の前回差分が小さい & 前回target が存在でプロンプトに含める。
                log(f"{file_info.source_file_path}の変更を検知しました。")
                log("ソースファイルの差分:")
                if os.path.exists(file_info.past_source_file_path):
                    return self.display_source_diff()
                # TODO: source のハッシュはあるのにsource 自体が無い場合は処理が止まるけどいいの？
                log_w(f"過去のソースファイルが存在しません: {file_info.past_source_file_path}")
            else:
                log_w(
                    f"埋め込まれたハッシュが存在しません。ファイルを削除してください。\n: {file_info.target_file_path}"
                )
                log_w("最後の10行:%s", "\n".join(lines[-10:]))
        return ""

    @log_inout
    def display_source_diff(self) -> str:
        file_info = self.magic_info.file_info
        import difflib

        with open(file_info.past_source_file_path, encoding="utf-8") as old_source_file:
            old_source_lines = old_source_file.readlines()
        with open(file_info.source_file_path, encoding="utf-8") as new_source_file:
            new_source_lines = new_source_file.readlines()

        source_diff = difflib.unified_diff(old_source_lines, new_source_lines, lineterm="", n=0)
        source_diff_text = "".join(source_diff)
        log("source_diff_text[:100]=%s", source_diff_text[:100])
        # TODO: source_diff_textをpromptに追加していいか？

        self.propose_target_diff(file_info.target_file_path, self.magic_info.prompt)
        log(f"ターゲットファイル: {file_info.target_file_path}")
        return file_info.target_file_path

    @log_inout
    def handle_new_target_file_py(self) -> str:
        """ソースコード(py_file)を新規作成する"""
        file_info = self.magic_info.file_info
        log(
            f"""
高級言語コンパイル中: {file_info.target_file_path}は新しいファイルです。少々お時間をいただきます。
{file_info.source_file_path} -> {file_info.target_file_path}
                """
        )
        target = TargetCodeGenerator(self.magic_info)
        return target.generate_target_code()

    @log_inout
    def handle_new_target_file_md(self) -> str:
        """要件定義書(md_file)を新規作成する
        TODO: BaseConverter.handle_new_target_file() に統合する"""
        file_info = self.magic_info.file_info
        log(
            f"""
    {"検索結果生成中" if self.magic_info.current_grimoire_name is None else "要件定義書執筆中"}:
    {file_info.target_file_path}は新しいファイルです。少々お時間をいただきます。
    {file_info.source_file_path} -> {file_info.target_file_path}
            """
        )
        return generate_md_from_prompt_recursive(self.magic_info)

    def propose_target_diff(self, target_file_path, prompt=None) -> None:
        """
        ターゲットファイルの変更差分を提案する関数(md/py共通)

        Args:
            target_file_path (str): 現在のターゲットファイルのパス
            prompt (str): promptの内容
        """
        # プロンプトにターゲットファイルの内容を変数として追加
        with open(target_file_path, encoding="utf-8") as target_file:
            current_target_code = target_file.read()
        prompt_additional_part = ""
        if prompt:
            prompt_additional_part = f"""
promptの内容:
{prompt}
をもとに、
"""
        prompt = f"""
現在のターゲットファイルの内容:
{current_target_code}

上記から
{prompt_additional_part}

ターゲットファイルの変更が必要な部分"のみ"をプログラムで出力してください。
出力はunified diff形式で、削除した文を薄い赤色、追加した文を薄い緑色にして

@@ -1,4 +1,4 @@
 line1
-line2
+line2 modified
 line3
-line4
+line4 modified

        """
        response = litellm.generate_response(
            model=settings.model_name_lite,
            prompt=prompt,
            max_tokens=1000,
            temperature=0.0,
        )
        target_diff = response.strip()
        # ターゲットファイルの差分を表示
        log("ターゲットファイルの差分(冒頭100字):")
        log(target_diff[:100])

        # ユーザーに適用方法を尋ねる
        log("差分をどのように適用しますか？")
        log("1. AIで適用する")
        choice = "1"

        while True:
            if choice == "1":
                # 差分をターゲットファイルに自動で適用
                self.apply_diff_to_target_file(target_file_path, target_diff)
                log(f"{target_file_path}に差分を自動で適用しました。")
                break
            log_e("論理異常： choice=%d", choice)
