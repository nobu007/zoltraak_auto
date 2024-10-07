import os

from zoltraak.schema.schema import FileInfo, MagicInfo
from zoltraak.utils.file_util import FileUtil
from zoltraak.utils.log_util import log, log_inout
from zoltraak.utils.rich_console import (
    display_magic_info_final,
    display_magic_info_full,
    display_magic_info_init,
    display_magic_info_intermediate,
)


class MagicWorkflow:
    def __init__(self, magic_info: MagicInfo = None):
        if magic_info is None:
            magic_info = MagicInfo()
        self.magic_info: MagicInfo = magic_info
        self.file_info: FileInfo = magic_info.file_info
        self.workflow_history = []
        self.start_workflow()

    @log_inout
    def start_workflow(self):
        # ワークフローを開始したときの共通処理
        log("ワークフローを開始します")
        display_magic_info_init(self.magic_info)
        self.file_info.update_work_dir()

    @log_inout
    def pre_process(self):
        # プロセスを実行する前の共通処理
        self.workflow_history.append(self.magic_info.description)
        display_magic_info_full(self.magic_info)

    @log_inout
    def run(self, func: callable):
        # プロセスを実行する
        self.pre_process()
        output_file_path = func()
        self.file_info.output_file_path = output_file_path
        self.post_process()
        self.display_result()
        return output_file_path

    @log_inout
    def post_process(self):
        # プロセスを実行した後の共通処理
        self.display_result()
        display_magic_info_intermediate(self.magic_info)
        log("プロセス完了： ↓実行履歴↓\n%s", self.workflow_history)

        # プロンプトを保存
        self.save_prompt()

        # target_file_pathにコピーを配置
        self.copy_output_to_target()

    @log_inout
    def display_result(self):
        # 結果を表示する
        log("結果:")
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
    def save_prompt(self):
        # work_dirからの相対パス取得
        target_file_path_rel = os.path.relpath(self.file_info.target_file_path, self.file_info.work_dir)

        # promptの保存先パス取得
        prompt_output_path = os.path.join(self.file_info.prompt_dir, target_file_path_rel + ".prompt")
        prompt_output_path_abs = os.path.abspath(prompt_output_path)

        # フォルダがない場合は作成
        os.makedirs(os.path.dirname(prompt_output_path_abs), exist_ok=True)

        # プロンプトを保存
        FileUtil.write_file(prompt_output_path_abs, self.magic_info.prompt)
        log("プロンプトを保存しました: %s", prompt_output_path_abs)

    @log_inout
    def copy_output_to_target(self) -> str:
        # target_file_pathとoutput_file_pathが異なる場合にコピーを配置する
        output_file_path_abs = os.path.abspath(self.file_info.output_file_path)
        target_file_path_abs = os.path.abspath(self.file_info.target_file_path)
        if output_file_path_abs != target_file_path_abs:
            # target_file_pathをコピーで更新
            FileUtil.copy_file(output_file_path_abs, target_file_path_abs)
            log("target_file_pathにコピーを配置しました。 : %s", target_file_path_abs)
        return target_file_path_abs

    @log_inout
    def end_workflow(self, final_output_file_path: str):
        # ワークフローを終了するときの共通処理
        self.file_info.final_output_file_path = final_output_file_path
        display_magic_info_final(self.magic_info)
        log("ワークフローを終了します")
