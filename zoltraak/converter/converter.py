import os

from zoltraak.converter.base_converter import BaseConverter
from zoltraak.core.magic_workflow import MagicWorkflow
from zoltraak.gencode import TargetCodeGenerator
from zoltraak.md_generator import generate_md_from_prompt_recursive
from zoltraak.schema.schema import MagicLayer
from zoltraak.utils.file_util import FileUtil
from zoltraak.utils.log_util import log, log_head, log_inout, log_w
from zoltraak.utils.subprocess_util import SubprocessUtil


class MarkdownToPythonConverter(BaseConverter):
    """マークダウン(要件定義書)からpythonコードを更新するコンバーター
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
    この処理はsourceの要求をtarget(マークダウン or Pythonコード)に反映することである。

    <LAYER_0(not active)>
    <LAYER_1(not active)>
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
        acceptable_layers = [
            MagicLayer.LAYER_4_REQUIREMENT_GEN,
            MagicLayer.LAYER_5_CODE_GEN,
            MagicLayer.LAYER_6_CODE_GEN,
        ]
        return self.magic_workflow.run_loop(self.convert, acceptable_layers)

    @log_inout
    def convert(self) -> str:
        """要件定義書(md_file) => Pythonコード"""

        # step1: ファイル情報を更新
        file_info = self.magic_info.file_info
        requirements_md_file_path = os.path.join(
            file_info.work_dir, "requirements", os.path.basename(file_info.md_file_path)
        )

        # step2: 要件定義書を更新
        if self.magic_info.magic_layer is MagicLayer.LAYER_4_REQUIREMENT_GEN:
            file_info.update_source_target(file_info.md_file_path, requirements_md_file_path)
            file_info.update_hash()

            return self.magic_workflow.run(self.convert_one_md_md)

        # step3: Pythonコードを作成
        if self.magic_info.magic_layer is MagicLayer.LAYER_5_CODE_GEN:
            file_info.update_source_target(requirements_md_file_path, file_info.py_file_path)
            file_info.update_hash()

            return self.magic_workflow.run(self.convert_one_md_py)

        return ""

    @log_inout
    def convert_one_md_md(self) -> str:
        """要件定義書(md_file) => 要件定義書(md_file)の１ファイルを変換する"""

        file_info = self.magic_info.file_info
        if FileUtil.has_content(file_info.target_file_path):  # -- マークダウンファイルのコンテンツが有効な場合
            if self.magic_workflow.prompt_manager.is_same_prompt():  # -- 前回と同じプロンプトの場合
                log(f"スキップ(既存＆input変更なし): {file_info.target_file_path}")
                return file_info.target_file_path  # --- 処理をスキップし既存のターゲットファイルを返す
            log(
                f"{file_info.target_file_path}は既存のファイルです。promptに従って変更を提案します。"
            )  # --- ファイルが既存であることを示すメッセージを表示
            return self.update_target_file_propose_and_apply(
                file_info.target_file_path, self.magic_info.prompt_goal
            )  # --- プロンプトに従ってターゲットファイルの差分を提案

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
                log("source_hash  =%s", file_info.source_hash)
                log_head("prompt=%s", self.magic_info.prompt_input)
                # TODO: 次処理に進むのプロンプトなし時だけなのか？全体に薄く適用するformatterみたいなケースは不要？
                if file_info.source_hash and file_info.source_hash == embedded_hash:
                    if self.magic_workflow.prompt_manager.is_same_prompt():  # -- 前回と同じプロンプトの場合
                        log(
                            f"prompt_inputの適用が完了しました。コード生成プロセスを開始します。{file_info.target_file_path}"
                        )
                        SubprocessUtil.run(["python", file_info.target_file_path], check=False)
                        return file_info.target_file_path  # TODO: サブプロセスで作った別ファイルの情報は不要？

                    # プロンプトがある場合はプロンプトを再適用してtargetを更新
                    SubprocessUtil.run(
                        [
                            "zoltraak",
                            file_info.canonical_name,
                            "-p",
                            self.magic_info.prompt_input,
                            "-ml",
                            self.magic_info.magic_layer,
                            "-mm",
                            "grimoire_only",
                        ],
                        check=False,
                    )
                    # target に埋め込まれたハッシュがsource (最新)に一致してたらスキップ
                    # TODO: ハッシュ運用検討
                    # source が同じでもコンパイラやプロンプトの更新でtarget が変わる可能性もある？
                    # どこかにtarget のinput全部を詰め込んだハッシュが必要？
                    return file_info.target_file_path

                # file_info.source_hash != embedded_hash または promptで修正要求がある場合
                # source が変わってたらtarget を作り直す
                # TODO: 前回のtarget を加味したほうが良い？
                # =>source の前回差分が小さい & 前回target が存在でプロンプトに含める。
                log(f"{file_info.source_file_path}の変更を検知しました。")
                log("ソースファイルの差分:")
                if os.path.exists(file_info.past_source_file_path):
                    return self.update_target_file_from_source_diff()
                log_w(f"過去のソースファイルが存在しないため再作成します: {file_info.past_source_file_path}")
                return self.handle_new_target_file_py()
            log_w(f"埋め込まれたハッシュが存在しないため再作成します。\n: {file_info.target_file_path}")
            log_w("最後の10行:%s", "\n".join(lines[-10:]))
            return self.handle_new_target_file_py()
        log_w(f"想定外の動作です。再作成します。\n: {file_info.target_file_path}")
        return self.handle_new_target_file_py()

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
要件定義書執筆中(requirements): {file_info.target_file_path}は新しいファイルです。少々お時間をいただきます。
{file_info.source_file_path} -> {file_info.target_file_path}
            """
        )
        return generate_md_from_prompt_recursive(self.magic_info)
