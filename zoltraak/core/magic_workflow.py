import os
from typing import TYPE_CHECKING

from zoltraak import settings
from zoltraak.converter.converter import MarkdownToPythonConverter
from zoltraak.converter.md_converter import MarkdownToMarkdownConverter
from zoltraak.core.prompt_manager import PromptManager
from zoltraak.generator.gencodebase import CodeBaseGenerator
from zoltraak.schema.schema import FileInfo, MagicInfo, MagicLayer, MagicMode
from zoltraak.utils.file_util import FileUtil
from zoltraak.utils.grimoires_util import GrimoireUtil
from zoltraak.utils.log_util import log, log_inout, log_w
from zoltraak.utils.rich_console import (
    display_magic_info_final,
    display_magic_info_full,
    display_magic_info_init,
    display_magic_info_intermediate,
    display_magic_info_post,
    display_magic_info_pre,
)

if TYPE_CHECKING:
    from zoltraak.converter.base_converter import BaseConverter


class MagicWorkflow:
    def __init__(self, magic_info: MagicInfo = None):
        if magic_info is None:
            magic_info = MagicInfo()
        self.magic_info: MagicInfo = magic_info
        self.file_info: FileInfo = magic_info.file_info
        self.prompt_manager: PromptManager = PromptManager(magic_info)
        self.converters: list[BaseConverter] = []
        self.workflow_history = []
        self.create_converters(self.magic_info, self.prompt_manager)

    @log_inout
    def create_converters(self, magic_info: MagicInfo, prompt_manager: PromptManager) -> None:
        self.converters.append(MarkdownToMarkdownConverter(magic_info, prompt_manager))
        self.converters.append(MarkdownToPythonConverter(magic_info, prompt_manager))
        self.converters.append(CodeBaseGenerator(magic_info, prompt_manager))

    @log_inout
    def start_workflow(self):
        # ワークフローを開始したときの共通処理
        log("ワークフローを開始します")
        display_magic_info_init(self.magic_info)
        log(f"display_magic_info_init called({self.magic_info.magic_layer})")
        self.file_info.update_work_dir()

    @log_inout
    def run_loop(self) -> str:
        """run処理をレイヤを進めながら繰り返す"""
        self.start_workflow()
        for layer in MagicLayer:
            if self.run_converters(layer):
                # ZOLTRAAK_LEGACYモードの場合は１回で終了
                if self.magic_info.magic_mode == MagicMode.ZOLTRAAK_LEGACY:
                    log("ZOLTRAAK_LEGACYモードにより、convert処理を終了します")
                    break

                # magic_layer_endで終了
                if self.magic_info.magic_layer == self.magic_info.magic_layer_end:
                    log("MAGIC_LAYER_ENDに到達したので、CONVERT処理を終了します")
                    break

                # 次のレイヤに進む
                self.magic_info.magic_layer = layer.next()
                log("end next = " + str(self.magic_info.magic_layer))

                # 次のレイヤにprompt_inputを再度渡さないようにモード変更
                log(f"magic_mode set {self.magic_info.magic_mode} => {MagicMode.GRIMOIRE_ONLY}")
                self.magic_info.magic_mode = MagicMode.GRIMOIRE_ONLY
                log("end next = " + str(self.magic_info.magic_layer))

        # ループの最後のoutput_file_pathをfinalとして設定して返す
        self.magic_info.file_info.final_output_file_path = self.magic_info.file_info.output_file_path
        return self.magic_info.file_info.final_output_file_path

    @log_inout
    def run_converters(self, layer: MagicLayer) -> bool:
        log("check layer = " + str(layer))
        is_called = False
        for converter in self.converters:
            if layer in converter.acceptable_layers and layer == self.magic_info.magic_layer:
                log(str(converter) + " convert layer = " + str(layer))
                self.run(converter.convert)
                is_called = True
        return is_called

    @log_inout
    def run(self, func: callable):
        # プロセスを実行する
        self.pre_process()
        output_file_path = func()
        display_magic_info_intermediate(self.magic_info)
        self.file_info.output_file_path = output_file_path
        self.post_process()
        self.display_result()
        return output_file_path

    @log_inout
    def pre_process(self):
        # プロセスを実行する前の共通処理
        log(f"pre_process called({self.magic_info.magic_layer})")
        display_magic_info_pre(self.magic_info)
        self.workflow_history.append(self.magic_info.description)

        # ソースファイルをprompt_goalに詰め込み
        prompt_goal = self.magic_info.prompt_input
        source_file_path = self.file_info.source_file_path
        if FileUtil.has_content(source_file_path):
            source_content = FileUtil.read_file(source_file_path)
            if prompt_goal.strip() != source_content.strip():
                log(f"ソースファイル読込:  {self.file_info.source_file_path}")
                self.magic_info.prompt_goal = self.magic_info.prompt_input
                prompt_goal += f"\n\n<<追加指示>>\n{source_content}"
        else:
            # ソースファイルを保存(設計では初回のprompt_file_pathにだけ保存する)
            log_w(f"ソースファイル更新(前レイヤ処理済？):  {source_file_path}")
            FileUtil.write_file(source_file_path, self.magic_info.prompt_input)

        # prompt_goalを更新
        self.magic_info.prompt_goal = prompt_goal

        # グリモアとプロンプトを更新(prompt_finalも更新)
        self.update_grimoire_and_prompt()

    @log_inout
    def post_process(self):
        # プロセスを実行した後の共通処理
        log("プロセス完了： ↓実行履歴↓\n%s", self.workflow_history)
        self.display_result()
        display_magic_info_post(self.magic_info)

        # プロンプトを保存
        self.prompt_manager.save_prompts()

        # target_file_pathにコピーを配置
        self.copy_output_to_target()

        # 過去のファイルを保存
        self.copy_past_files()

        log(f"post_process called({self.magic_info.magic_layer})")

    @log_inout
    def display_result(self):
        # 結果を表示する
        if settings.is_debug:
            display_magic_info_full(self.magic_info)
        log("結果: is_success=%s", self.magic_info.is_success)
        if self.magic_info.is_success:
            log(self.magic_info.success_message)
        else:
            log(self.magic_info.error_message)

    @log_inout
    def display_progress(self):
        # 進捗を表示する
        log(f"実行中レイヤ: {self.magic_info.magic_layer}")

    @log_inout
    def create_folder(self):
        # フォルダを作成する
        pass

    @log_inout
    def update_grimoire_and_prompt(self):
        # モードによる分岐
        log(f"{self.magic_info.magic_mode}で変更を提案します。")

        # コンパイラのパスを取得
        compiler_path = GrimoireUtil.get_valid_compiler(self.magic_info.grimoire_compiler)
        default_compiler_path = GrimoireUtil.get_valid_compiler("general_prompt.md")

        if self.magic_info.magic_mode is MagicMode.GRIMOIRE_ONLY:
            # グリモアのみ
            if not os.path.isfile(compiler_path):
                log("コンパイラが存在しないため、デフォルトのコンパイラを使用します。")
                compiler_path = default_compiler_path
            self.magic_info.prompt_input = ""
        elif self.magic_info.magic_mode is MagicMode.GRIMOIRE_AND_PROMPT:
            # グリモアまたはプロンプトどちらか TODO: 用語をコンパイラに統一したい
            if not os.path.isfile(compiler_path):
                compiler_path = ""
                if not self.magic_info.prompt_input:
                    log("コンパイラもプロンプトも未設定のため、一般的なプロンプトを使用します。")
                    compiler_path = ""
                    self.magic_info.prompt_input = FileUtil.read_grimoire(default_compiler_path)
        elif self.magic_info.magic_mode is MagicMode.PROMPT_ONLY:
            # プロンプトのみ
            compiler_path = ""
            if not self.magic_info.prompt_input:
                log("プロンプトが未設定のため、一般的なプロンプトを使用します。")
                self.magic_info.prompt_input = FileUtil.read_grimoire(default_compiler_path)
        else:
            # SEARCH_GRIMOIRE or ZOLTRAAK_LEGACY(ノーケア、別のところで処理すること！)
            log("(SEARCH_GRIMOIRE)一般的なプロンプトを使用します。")
            if not os.path.isfile(compiler_path):
                compiler_path = default_compiler_path
                self.magic_info.prompt_input = FileUtil.read_grimoire(default_compiler_path)

        # grimoire_compiler更新
        self.magic_info.grimoire_compiler = compiler_path
        log("grimoire_compilerを更新しました。 %s", self.magic_info.grimoire_compiler)

        # prompt_finalを更新
        self.prompt_manager.prepare_prompt_final()

    @log_inout
    def copy_output_to_target(self) -> str:
        # target_file_pathとoutput_file_pathが異なる場合にコピーを配置する
        output_file_path_abs = os.path.abspath(self.file_info.output_file_path)
        target_file_path_abs = os.path.abspath(self.file_info.target_file_path)
        if os.path.isfile(output_file_path_abs) and output_file_path_abs != target_file_path_abs:
            # target_file_pathをコピーで更新
            FileUtil.copy_file(output_file_path_abs, target_file_path_abs)
            log(f"output_file_pathとtarget_file_pathが異なります。コピーを配置しました、{target_file_path_abs}")
            self.file_info.target_file_path = output_file_path_abs
            log(f"target_file_pathが更新されました。{target_file_path_abs} -> {output_file_path_abs}")
        else:
            log("output_file_pathコピー不要 %s", output_file_path_abs)
        return target_file_path_abs

    @log_inout
    def copy_past_files(self) -> None:
        # ソースは固定場所なのでfile_infoの情報を使う
        if os.path.isfile(self.file_info.source_file_path):
            os.makedirs(os.path.dirname(self.file_info.past_source_file_path), exist_ok=True)
            FileUtil.copy_file(self.file_info.source_file_path, self.file_info.past_source_file_path)
            log("past_source_file_path にコピーを配置しました。 : %s", self.file_info.past_source_file_path)

        # 変換後のファイルは配置先がoutput_path起因でtarget_file_path が更新されているので、相対パスを使う
        if os.path.isfile(self.file_info.target_file_path):
            self.copy_file_by_rel_path(self.file_info.target_file_path, self.file_info.past_target_dir)

    @log_inout
    def copy_file_by_rel_path(self, origin_file_path: str, destination_dir: str, origin_base_dir: str = "") -> str:
        """コピー元ファイルを、コピー先のディレクトリ配下に、元のディレクトリ構造を保持してコピーする。
        基準ディレクトリのデフォルト値はwork_dir

        Args:
            origin_base_dir (str): origin_file_pathのどこからディレクトリ構造を保持するか
        """
        if origin_base_dir == "":
            origin_base_dir = self.file_info.work_dir

        # past_source_file_path
        origin_file_path_abs = os.path.abspath(origin_file_path)
        if os.path.isfile(origin_file_path_abs):
            origin_file_path_rel = os.path.relpath(origin_file_path_abs, origin_base_dir)
            destination_file_path = os.path.join(destination_dir, origin_file_path_rel)
            destination_file_path_abs = os.path.abspath(destination_file_path)
            os.makedirs(os.path.dirname(destination_file_path_abs), exist_ok=True)
            FileUtil.copy_file(origin_file_path_abs, destination_file_path_abs)
            log("past_source_file_path にコピーを配置しました。 : %s", destination_file_path_abs)
            return destination_file_path_abs
        log("コピー元ファイルがないためコピーできませんでした。 %s", origin_file_path_abs)
        return ""

    @log_inout
    def end_workflow(self, final_output_file_path: str):
        # ワークフローを終了するときの共通処理
        log("ワークフローを終了します")
        self.file_info.final_output_file_path = final_output_file_path
        display_magic_info_final(self.magic_info)
        log(f"display_magic_info_final called({self.magic_info.magic_layer})")

    def __str__(self) -> str:
        return f"MagicWorkflow({self.magic_info.description})"

    def __repr__(self) -> str:
        return self.__str__()
