import os

from zoltraak.analyzer.dependency_map.python.dependency_manager_py import DependencyManagerPy
from zoltraak.converter.base_converter import BaseConverter
from zoltraak.core.prompt_manager import PromptEnum, PromptManager
from zoltraak.gencode import TargetCodeGenerator
from zoltraak.schema.schema import MagicInfo, MagicLayer
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

    <LAYER_1(not active)>
    <LAYER_2(not active)>
    <LAYER_3(not active)>
    <LAYER_4>
      source => md_file_path
      target => requirements/md_file_path
    <LAYER_5>
      source => requirements/md_file_path
      target => py_file_path
    <LAYER_5.1>
      source => structure_file_path
      target => dependency_file_path
    """

    def __init__(self, magic_info: MagicInfo, prompt_manager: PromptManager):
        super().__init__(magic_info, prompt_manager)
        self.magic_info = magic_info
        self.prompt_manager = prompt_manager
        self.acceptable_layers = [
            MagicLayer.LAYER_4_REQUIREMENT_GEN,
            MagicLayer.LAYER_5_CODE_GEN,
            MagicLayer.LAYER_5_1_DEPENDENCY_GEN,
        ]
        self.name = "MarkdownToPythonConverter"

    @log_inout
    def prepare(self) -> None:
        """prompt + ユーザ要求記述書(pre_md_file) => 要件定義書(md_file)"""
        super().prepare()

        # step1: ファイル情報を更新
        file_info = self.magic_info.file_info
        requirements_md_file_path = os.path.join(
            file_info.work_dir, "requirements", "def_" + os.path.basename(file_info.md_file_path)
        )

        # step2: 要件定義書を更新
        if self.magic_info.magic_layer is MagicLayer.LAYER_4_REQUIREMENT_GEN:
            file_info.update_source_target(
                file_info.md_file_path, requirements_md_file_path, file_info.structure_file_path
            )

        # step3: Pythonコードを作成
        if self.magic_info.magic_layer is MagicLayer.LAYER_5_CODE_GEN:
            file_info.update_source_target(
                requirements_md_file_path, file_info.py_file_path, file_info.structure_file_path
            )

        # step4: dependencyファイルを作成
        if self.magic_info.magic_layer is MagicLayer.LAYER_5_1_DEPENDENCY_GEN:
            file_info.update_source_target(file_info.structure_file_path, file_info.dependency_file_path)

    @log_inout
    def convert(self) -> float:
        """要件定義書(md_file) => Pythonコード"""

        # LAYER_4_REQUIREMENT_GEN
        if self.magic_info.magic_layer is MagicLayer.LAYER_4_REQUIREMENT_GEN:
            return self.convert_one()
        # MagicLayer.LAYER_5_CODE_GEN
        if self.magic_info.magic_layer is MagicLayer.LAYER_5_CODE_GEN:
            return self.convert_one_md_py()
        # MagicLayer.LAYER_5_1_DEPENDENCY_GEN
        return self.convert_one_dependency()

    @log_inout
    def convert_one_md_py(self) -> float:
        """要件定義書(md_file) => my or pyの１ファイルを変換する"""
        if FileUtil.has_content(self.magic_info.file_info.target_file_path):
            output_file_path = self.handle_existing_target_file_py()
            target = TargetCodeGenerator(self.magic_info, self.litellm_api)
            target.last_code = FileUtil.read_file(output_file_path)  # converterの更新結果を最終コードとして採用
            # TODO: このタイミングでprocess_generated_code()する？
            target.write_code_to_target_file(output_file_path)  # HASHを埋め込む
            return output_file_path
        return self.handle_new_target_file()

    @log_inout
    def convert_one_dependency(self) -> float:
        """dependencyファイルを作成"""
        dm = DependencyManagerPy(self.magic_info.file_info.target_dir)
        dm.scan_project()
        dm.write_dependency_file(self.magic_info.file_info.dependency_file_path)
        return self.get_score_from_target_content()

    @log_inout
    def handle_existing_target_file_py(self) -> float:  # noqa: PLR0911
        file_info = self.magic_info.file_info
        with open(file_info.target_file_path, encoding="utf-8") as target_file:
            lines = target_file.readlines()
            if len(lines) > 0 and lines[-1].startswith("# HASH: "):
                embedded_hash = lines[-1].split("# HASH: ")[1].strip()
                log("embedded_hash=%s", embedded_hash)
                log("source_hash  =%s", file_info.source_hash)
                log_head("prompt_input=%s", self.magic_info.prompt_input)
                # TODO: 次処理に進むのプロンプトなし時だけなのか？全体に薄く適用するformatterみたいなケースは不要？
                if file_info.source_hash and file_info.source_hash == embedded_hash:
                    # 重要: is_same_promptはpast_promptとself.magic_infoを比較するため、ここで設定する必要がある
                    PromptEnum.INPUT.set_current_prompt(self.magic_info.prompt_final, self.magic_info)
                    if self.prompt_manager.is_same_prompt(
                        self.magic_info, PromptEnum.FINAL
                    ):  # -- 前回と同じプロンプトの場合
                        log("過去のターゲットファイルと同一のためコード生成をスキップします。")
                        self.magic_info.history_info += " ->コード生成をスキップ"
                        return self.get_score_from_target_content()

                    # 前回のプロンプトと異なる場合は再適用してコード生成
                    output_file_path = self.handle_existing_target_file()
                    log(f"prompt_inputの適用が完了しました。コード生成プロセスを開始します。{output_file_path}")
                    self.magic_info.history_info += " ->コード生成開始"
                    SubprocessUtil.run(["python", output_file_path], check=False)
                    log("コード生成プロセスが完了しました。")
                    self.magic_info.history_info += " ->コード生成完了"
                    return self.get_score_from_target_content()  # TODO: サブプロセスで作った別ファイルの情報は不要？

                    # TODO: ハッシュ運用検討
                    # source が同じでもコンパイラやプロンプトの更新でtarget が変わる可能性もある？
                    # どこかにtarget のinput全部を詰め込んだハッシュが必要？

                # file_info.source_hash != embedded_hash または promptで修正要求がある場合
                # source が変わってたらtarget を作り直す
                # TODO: 前回のtarget を加味したほうが良い？
                # =>source の前回差分が小さい & 前回target が存在でプロンプトに含める。
                log(f"{file_info.source_file_path}の変更を検知しました。")
                self.magic_info.history_info += " ->再作成(ソース変更)"
                return self.handle_new_target_file_py()
            log_w(f"埋め込まれたハッシュが存在しないため再作成します。\n: {file_info.target_file_path}")
            log_w("最後の10行:%s", "\n".join(lines[-10:]))
            self.magic_info.history_info += " ->再作成(hashなし)"
            return self.handle_new_target_file_py()
        log_w(f"想定外の動作です。再作成します。\n: {file_info.target_file_path}")
        self.magic_info.history_info += " ->再作成(想定外)"
        return self.handle_new_target_file_py()


#     @log_inout
#     def handle_new_target_file_md(self) -> str:
#         """要件定義書(md_file)を新規作成する
#         TODO: BaseConverter.handle_new_target_file() に統合する"""
#         file_info = self.magic_info.file_info
#         log(
#             f"""
# 要件定義書執筆中(requirements): {file_info.target_file_path}は新しいファイルです。少々お時間をいただきます。
# {file_info.source_file_path} -> {file_info.target_file_path}
#             """
#         )
#         self.magic_info.history_info += " ->要件定義(requirements)新規作成"
#         return self.generate_md_from_prompt(self.magic_info)
