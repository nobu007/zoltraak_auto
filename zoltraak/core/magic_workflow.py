import asyncio
import copy
import os
import sys

import anyio
from tqdm import tqdm
from tqdm.asyncio import tqdm_asyncio

from zoltraak import settings
from zoltraak.converter.base_converter import BaseConverter
from zoltraak.converter.converter import MarkdownToPythonConverter
from zoltraak.converter.md_converter import MarkdownToMarkdownConverter
from zoltraak.core.prompt_manager import PromptManager
from zoltraak.generator.file_analyzer import FileAnalyzer
from zoltraak.generator.file_remover import FileRemover
from zoltraak.generator.gencode import CodeGenerator
from zoltraak.generator.gencodebase import CodeBaseGenerator
from zoltraak.schema.schema import FileInfo, MagicInfo, MagicLayer, MagicMode, MagicWorkflowInfo, SourceTargetSet
from zoltraak.utils.diff_util import DiffUtil
from zoltraak.utils.file_util import FileUtil
from zoltraak.utils.grimoires_util import GrimoireUtil
from zoltraak.utils.log_util import log, log_change, log_head_diff, log_i, log_inout, log_progress
from zoltraak.utils.rich_console import (
    display_magic_info_final,
    display_magic_info_full,
    display_magic_info_init,
    display_magic_info_intermediate,
    display_magic_info_post,
    display_magic_info_pre,
)


class MagicWorkflow:
    def __init__(self, magic_info: MagicInfo = None):
        self.magic_workflow_info: MagicWorkflowInfo = MagicWorkflowInfo()
        if magic_info is None:
            magic_info = MagicInfo()
        self.magic_info: MagicInfo = magic_info
        self.file_info: FileInfo = magic_info.file_info
        self.prompt_manager: PromptManager = PromptManager()
        self.converters: list[BaseConverter] = []
        self.workflow_history = []
        self.create_converters(self.magic_info, self.prompt_manager)

    @log_inout
    def create_converters(self, magic_info: MagicInfo, prompt_manager: PromptManager) -> None:
        self.converters.append(FileAnalyzer(magic_info, prompt_manager))
        self.converters.append(MarkdownToMarkdownConverter(magic_info, prompt_manager))
        if self.magic_info.magic_mode == MagicMode.ZOLTRAAK_LEGACY:
            # ZOLTRAAK_LEGACYモード(高速生成モード: input ⇒ 要件定義書 ⇒ code)
            self.converters.append(MarkdownToPythonConverter(magic_info, prompt_manager))
        else:
            # 詳細モード
            self.converters.append(CodeGenerator(magic_info, prompt_manager))
        self.converters.append(CodeBaseGenerator(magic_info, prompt_manager))
        self.converters.append(FileRemover(magic_info, prompt_manager))

    @log_inout
    def start_workflow(self):
        # ワークフローを開始したときの共通処理
        log(self.get_log("ワークフローを開始します"))
        display_magic_info_init(self.magic_info)
        log(self.get_log(f"display_magic_info_init called({self.magic_info.magic_layer})"))
        self.file_info.update_work_dir()

    @log_inout
    def run_loop(self) -> str:
        """run処理をレイヤを進めながら繰り返す"""
        self.start_workflow()
        while True:
            is_called, score_list = self.run_converters(self.magic_info.magic_layer)
            log("is_called=%s, score_list=%s", is_called, score_list)

            # ループ終了条件
            if self.magic_info.magic_layer == self.magic_info.magic_layer_end:
                break

            # 次のレイヤに進む
            self.magic_info.magic_layer = self.magic_info.magic_layer.next()
            log(self.get_log("end next = " + str(self.magic_info.magic_layer)))

            # 次のレイヤにprompt_inputを再度渡さないようにモード変更
            log(self.get_log(f"magic_mode set {self.magic_info.magic_mode} => {MagicMode.GRIMOIRE_ONLY}"))
            self.magic_info.magic_mode = MagicMode.GRIMOIRE_ONLY

        # ループの最後のoutput_file_pathをfinalとして設定して返す
        self.magic_info.file_info.final_output_file_path = self.magic_info.file_info.output_file_path

        self.end_workflow(self.magic_info)

        return self.magic_info.file_info.final_output_file_path

    @log_inout
    def run_converters(self, layer: MagicLayer) -> tuple[bool, list[float]]:
        log(self.get_log("check layer = " + str(layer)))
        is_called = False
        score_list = []
        for converter in self.converters:
            if layer in converter.acceptable_layers and layer == self.magic_info.magic_layer:
                log_i(self.get_log(str(converter) + " convert layer = " + str(layer)))
                converter.prepare()
                is_gen, score = self.run_converter(converter)
                is_called = True
                score_list.append(score)
        return is_called, score_list

    @log_inout
    def run_converter(self, converter: BaseConverter) -> tuple[bool, float]:
        is_gen = False
        if hasattr(converter, "prepare_generation") and callable(converter.prepare_generation):
            # ジェネレータ
            source_target_set_list = converter.prepare_generation()
            if not source_target_set_list:
                log("source_target_set_list empty")
                self.workflow_history.append(self.magic_info.magic_layer + "(source_target_set_list empty)")
                return True, -1.0

            # 非同期用の設定に変更
            self.magic_info.is_async = True

            # プログレスバーを初期化
            progress_bar = tqdm_asyncio(
                total=len(source_target_set_list),
                unit="files",
                file=sys.stdout,
                desc=self.magic_info.magic_layer + "(run_converter)",
            )

            # 非同期処理を実行
            score = anyio.run(self.process_source_target_sets, converter, source_target_set_list, progress_bar)
            log("process_source_target_sets are completed score=%f", score)

            progress_bar.close()

            # 非同期処理の結果を集約
            for magic_info in self.magic_workflow_info.magic_info_list:
                self.workflow_history.append(magic_info.history_info)

            # 非同期用の設定を解除
            self.magic_info.is_async = False

            is_gen = True
        else:
            # コンバーター
            log(self.get_log(f"run Converter target_file_path = {self.file_info.target_file_path}"))
            score = self.run(converter.convert, self.magic_info)
        return is_gen, score

    async def process_source_target_sets(
        self, converter: BaseConverter, source_target_set_list: list[SourceTargetSet], progress_bar: tqdm
    ):
        # 同一のターゲットファイルのソースファイルをマージする
        target_source_map = {}
        target_context_map = {}
        for source_target_set in source_target_set_list:
            target = source_target_set.target_file_path
            source = source_target_set.source_file_path
            context = source_target_set.context_file_path
            if target in target_source_map:
                target_source_map[target].append(source)
            else:
                target_source_map[target] = [source]
            target_context_map[target] = context  # コンテキストファイルは最後のものを使う

        # マージしたソースファイルをSourceTargetSetに戻す
        source_target_set_list_merged = []
        for target, source in target_source_map.items():
            source_target_set = SourceTargetSet()
            if len(source) > 1:
                # 複数のソースファイルをマージ
                source_file_content_all = ""
                for source_file_path in source:
                    source_file_content_all += f"<<<{source_file_path}>>>\n"
                    source_file_content_all += FileUtil.read_file(source_file_path)
                    source_file_content_all += "\n\n"

                split_ext = os.path.splitext(source[0])
                source_file_path_merged = split_ext[0] + "_merged" + split_ext[1]
                FileUtil.write_file(source_file_path_merged, source_file_content_all)
                log(self.get_log(f"merge source files = {source}"))
            else:
                # 単一のソースファイルはそのまま追加
                source_file_path_merged = source[0]
            source_target_set.source_file_path = source_file_path_merged
            source_target_set.target_file_path = target
            source_target_set.context_file_path = target_context_map[target]
            source_target_set_list_merged.append(source_target_set)

        # 非同期処理を実行
        tasks = []
        for source_target_set in source_target_set_list_merged:
            task = self.process_single_set(converter, source_target_set, progress_bar)
            tasks.append(task)
        tqdm_asyncio.as_completed(await asyncio.gather(*tasks, return_exceptions=True))

    async def process_single_set(
        self, converter: BaseConverter, source_target_set: SourceTargetSet, progress_bar: tqdm
    ):
        log_progress(progress_bar)

        # 非同期用のオブジェクトをコピー
        converter_copy = copy.copy(converter)
        magic_info_copy = copy.copy(converter_copy.magic_info)
        file_info_copy = copy.copy(magic_info_copy.file_info)
        self.magic_workflow_info.magic_info_list.append(magic_info_copy)
        # コピーしたオブジェクト間の参照関係を設定
        converter_copy.magic_info = magic_info_copy
        magic_info_copy.file_info = file_info_copy
        # SourceTargetSetをコピーに反映
        file_info_copy.update_source_target(
            source_target_set.source_file_path,
            source_target_set.target_file_path,
            source_target_set.context_file_path,
        )
        file_info_copy.update_hash()
        log(self.get_log(f"run Generator source_target_set = {source_target_set}"))
        await anyio.to_thread.run_sync(self.run, converter_copy.convert, magic_info_copy)
        progress_bar.update(1)

    # async def async_run(self, convert_method: callable, magic_info: MagicInfo):
    #     # convert_method が非同期の場合
    #     if inspect.iscoroutinefunction(convert_method):
    #         await convert_method(magic_info)
    #     else:
    #         # convert_method が同期の場合、別スレッドで実行
    #         await anyio.to_thread.run_sync(self.run, convert_method, magic_info)

    @log_inout
    def run(self, func: callable, magic_info: MagicInfo):
        # プロセスを実行する
        # 超重要: このメソッドは、並列処理をするためmagic_infoを引き回す。self.magic_infoなどは使用禁止！
        self.pre_process(magic_info)
        score = func()
        log(self.get_log(f"score= {score}"))
        magic_info.score = score
        display_magic_info_intermediate(magic_info)
        self.post_process(magic_info)
        self.display_result(magic_info)
        return score

    @log_inout
    def pre_process(self, magic_info: MagicInfo):
        # プロセスを実行する前の共通処理
        file_info = magic_info.file_info
        log(self.get_log(f"プロセス開始: {magic_info.magic_layer}"))
        display_magic_info_pre(magic_info)
        magic_info.history_info = ""

        # ソースファイルをprompt_goalに詰め込み
        prompt_goal = magic_info.prompt_input
        source_file_path = file_info.source_file_path

        if FileUtil.has_content(source_file_path):
            source_content = FileUtil.read_file(source_file_path)
            # prompt_inputがsource_content由来の場合に備えて同一チェック
            if not DiffUtil.is_contain_ignore_space(prompt_goal, source_content):
                log(self.get_log(f"ソースファイル読込:  {file_info.source_file_path}"))
                prompt_goal += f"\n\n<<追加情報>>\n{source_content}"
        else:
            # ソースファイルを保存(設計では初回のprompt_file_pathにだけ保存する)
            log(self.get_log(f"ソースファイル更新(前レイヤ処理済？):  {source_file_path}"))
            FileUtil.write_file(source_file_path, magic_info.prompt_input)

        # コンテキストファイルをprompt_goalに詰め込み
        context_file_path = file_info.context_file_path
        if FileUtil.has_content(context_file_path):
            context_content = FileUtil.read_file(context_file_path)
            log(self.get_log(f"コンテキストファイル読込:  {context_file_path}"))
            prompt_goal += f"\n\n<<背景情報>>\n{context_content}"

        # prompt_goalを更新
        magic_info.prompt_goal = prompt_goal

        # グリモアとプロンプトを更新(prompt_finalも更新)
        self.update_grimoire_and_prompt(magic_info)

    @log_inout
    def post_process(self, magic_info: MagicInfo):
        # プロセスを実行した後の共通処理
        file_info = magic_info.file_info
        log(self.get_log(f"プロセス完了: {magic_info.magic_layer}"))
        self.display_result(magic_info)
        display_magic_info_post(magic_info)

        # プロンプトを保存（実行時にも保存するが、prompt_finalとかが保存できないので、ここでも保存）
        self.prompt_manager.save_prompts(magic_info)

        # target_file_pathにコピーを配置(非同期実行のoutputが未設定なので無効化 TODO: 非同期の結果をoutputに設定)
        # self.copy_output_to_target(magic_info)

        # 過去のファイルを保存
        self.copy_past_files(magic_info)

        # history_infoを更新 例: layer_5_code_gen(main.md ->スキップ(既存＆input変更なし))
        magic_info.history_info = (
            "    " + magic_info.magic_layer + f"(target: {file_info.target_file_name}{magic_info.history_info})"
        )
        self.workflow_history.append(magic_info.history_info)

        log(self.get_log(f"post_process called({magic_info.magic_layer})"))

    @log_inout
    def display_result(self, magic_info: MagicInfo):
        # 結果を表示する
        if settings.is_debug:
            display_magic_info_full(magic_info)
        log(self.get_log(f"結果: is_success={magic_info.is_success}"))
        if magic_info.is_success:
            log(self.get_log(magic_info.success_message))
        else:
            log(self.get_log(magic_info.error_message))

    @log_inout
    def display_progress(self, magic_info: MagicInfo):
        # 進捗を表示する
        log(self.get_log(f"実行中レイヤ: {magic_info.magic_layer}"))

    @log_inout
    def create_folder(self):
        # フォルダを作成する
        pass

    @log_inout
    def update_grimoire_and_prompt(self, magic_info: MagicInfo):
        """MagicModeによって起動時のprompt_inputとグリモアを変更する。
        ちなみにsource_file_pathで指定されたインプットファイルはpre_process()で詰め込む(重要)。
        """
        # モードによる分岐
        log(self.get_log(f"{magic_info.magic_mode}で変更中。現状: {magic_info.grimoire_compiler}"))

        # コンパイラのパスを取得
        compiler_path = GrimoireUtil.get_valid_compiler(magic_info.grimoire_compiler)
        default_compiler_path = GrimoireUtil.get_valid_compiler("general_prompt.md")

        prompt_input_new = magic_info.prompt_input
        compiler_path_new = compiler_path
        if magic_info.magic_mode is MagicMode.GRIMOIRE_ONLY:
            # グリモアのみ
            if not os.path.isfile(compiler_path):
                log(self.get_log("コンパイラが存在しないため、デフォルトのコンパイラを使用します。"))
                compiler_path_new = default_compiler_path
            prompt_input_new = ""
        elif magic_info.magic_mode is MagicMode.GRIMOIRE_AND_PROMPT:
            # グリモアまたはプロンプトどちらか TODO: 用語をコンパイラに統一したい
            if not os.path.isfile(compiler_path):
                compiler_path_new = ""
                if not magic_info.prompt_input:
                    log(self.get_log("コンパイラもプロンプトも未設定のため、一般的なプロンプトを使用します。"))
                    prompt_input_new = FileUtil.read_file(default_compiler_path)
        elif magic_info.magic_mode is MagicMode.PROMPT_ONLY:
            # プロンプトのみ
            compiler_path_new = ""
            if not magic_info.prompt_input:
                log(self.get_log("プロンプトが未設定のため、一般的なプロンプトを使用します。"))
                prompt_input_new = FileUtil.read_file(default_compiler_path)
        else:
            # SEARCH_GRIMOIRE or ZOLTRAAK_LEGACY(ノーケア、別のところで処理すること！)
            log(self.get_log("(SEARCH_GRIMOIRE)一般的なプロンプトを使用します。"))
            if not os.path.isfile(compiler_path):
                compiler_path_new = default_compiler_path
                prompt_input_new = FileUtil.read_file(default_compiler_path)

        # prompt_inputを更新
        log_head_diff("prompt_input更新", magic_info.prompt_input, prompt_input_new)
        magic_info.prompt_input = prompt_input_new

        # grimoire_compiler更新
        log_change("grimoire_compiler更新", magic_info.grimoire_compiler, compiler_path_new)
        magic_info.grimoire_compiler = compiler_path_new

        # prompt_finalを更新
        self.prompt_manager.prepare_prompt_final(magic_info)

    @log_inout
    def copy_output_to_target(self, magic_info: MagicInfo) -> str:
        file_info = magic_info.file_info
        # target_file_pathとoutput_file_pathが異なる場合にコピーを配置する
        output_file_path_abs = os.path.abspath(file_info.output_file_path)
        target_file_path_abs = os.path.abspath(file_info.target_file_path)
        if os.path.isfile(output_file_path_abs) and output_file_path_abs != target_file_path_abs:
            # target_file_pathをコピーで更新
            FileUtil.copy_file(output_file_path_abs, target_file_path_abs)
            log(
                self.get_log(
                    f"output_file_pathとtarget_file_pathが異なります。コピーを配置しました、{target_file_path_abs}"
                )
            )
            file_info.target_file_path = output_file_path_abs
            log_change(self.get_log("target_file_pathが更新されました。"), target_file_path_abs, output_file_path_abs)
        else:
            log(self.get_log(f"output_file_pathコピー不要です。 :  {output_file_path_abs}"))
        return target_file_path_abs

    @log_inout
    def copy_past_files(self, magic_info: MagicInfo) -> None:
        file_info = magic_info.file_info
        # ソースを past_source_dir にコピー
        if os.path.isfile(file_info.source_file_path):
            FileUtil.copy_file(file_info.source_file_path, file_info.past_source_file_path)

        # ターゲットを past_target_dir にコピー
        if os.path.isfile(file_info.target_file_path):
            FileUtil.copy_file(file_info.target_file_path, file_info.past_target_file_path)

    # @log_inout
    # def copy_file_by_rel_path(self, origin_file_path: str, destination_dir: str, origin_base_dir: str) -> str:
    #     """コピー元ファイルを、コピー先のディレクトリ配下に、元のディレクトリ構造を保持してコピーする。
    #     基準ディレクトリのデフォルト値はwork_dir

    #     Args:
    #         origin_base_dir (str): origin_file_pathのどこからディレクトリ構造を保持するか
    #     """

    #     # past_source_file_path or past_target_file_path にコピーを配置する
    #     origin_file_path_abs = os.path.abspath(origin_file_path)
    #     if os.path.isfile(origin_file_path_abs):
    #         origin_file_path_rel = os.path.relpath(origin_file_path_abs, origin_base_dir)
    #         destination_file_path = os.path.join(destination_dir, origin_file_path_rel)
    #         destination_file_path_abs = os.path.abspath(destination_file_path)
    #         os.makedirs(os.path.dirname(destination_file_path_abs), exist_ok=True)
    #         FileUtil.copy_file(origin_file_path_abs, destination_file_path_abs)
    #         log(self.get_log(f"pastファイルをコピーしました。 : {destination_file_path_abs}"))
    #         return destination_file_path_abs
    #     log(self.get_log(f"コピー元ファイルがないためコピーできませんでした。 : {origin_file_path_abs}"))
    #     return ""

    @log_inout
    def end_workflow(self, magic_info: MagicInfo):
        # ワークフローを終了するときの共通処理
        log(self.get_log("ワークフローを終了します"))

        display_magic_info_final(magic_info)
        log_i("プロセス履歴=\n%s", "\n".join(self.workflow_history))
        log(self.get_log(f"display_magic_info_final called({self.magic_info.magic_layer})"))

    def get_log(self, msg: str):
        return f"{self.magic_info.magic_layer} : {msg}"

    def __str__(self) -> str:
        return f"MagicWorkflow({self.magic_info.description})"

    def __repr__(self) -> str:
        return self.__str__()
