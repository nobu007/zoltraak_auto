import os
from enum import Enum

from zoltraak.schema.schema import FileInfo, MagicInfo
from zoltraak.utils.file_util import FileUtil
from zoltraak.utils.log_util import log, log_inout


class PromptEnum(str, Enum):
    INPUT = "_input"
    MATCH_RATE = "_match_rate"
    DIFF_ORDER = "_diff_order"
    DIFF = "_diff"
    APPLY = "_apply"
    GOAL = "_goal"
    FINAL = "_final"

    def get_prompt_file_path(self, target_file_path_rel: str, magic_info: MagicInfo) -> None:
        prompt_output_path = os.path.join(
            magic_info.file_info.prompt_dir, magic_info.magic_layer, target_file_path_rel + self.value + ".prompt"
        )
        return os.path.abspath(prompt_output_path)

    def get_current_prompt(self, magic_info: MagicInfo) -> str:
        current_prompt_attr = f"prompt{self.value}"
        log("current_prompt_attr=%s", current_prompt_attr)
        return getattr(magic_info, current_prompt_attr)

    def __str__(self) -> str:
        return f"PromptEnum({self.name})"

    def __repr__(self) -> str:
        return self.__str__()


class PromptManager:
    def __init__(self, magic_info: MagicInfo = None):
        self.magic_info: MagicInfo = magic_info
        self.file_info: FileInfo = magic_info.file_info

    @log_inout
    def save_prompts(self) -> None:
        # work_dirからの相対パス取得
        target_file_path_rel = os.path.relpath(self.file_info.target_file_path, self.file_info.work_dir)

        # promptの保存先パス取得
        for prompt_enum in PromptEnum:
            self.save_prompt(prompt_enum.get_current_prompt(self.magic_info), target_file_path_rel, prompt_enum)
            # (例)self.save_prompt(self.magic_info.prompt_input, target_file_path_rel, "_input")

    @log_inout
    def save_prompt(self, prompt: str, target_file_path_rel: str, prompt_enum: PromptEnum = PromptEnum.INPUT) -> None:
        if prompt == "":
            return

        prompt_output_path = prompt_enum.get_prompt_file_path(target_file_path_rel, self.magic_info)

        # フォルダがない場合は作成
        os.makedirs(os.path.dirname(prompt_output_path), exist_ok=True)

        # プロンプトを保存
        FileUtil.write_file(prompt_output_path, prompt)
        log("プロンプトを保存しました %s: %s", prompt_enum, prompt_output_path)

    @log_inout
    def load_prompt(self, prompt_enum: PromptEnum = PromptEnum.INPUT) -> str:
        # work_dirからの相対パス取得
        target_file_path_rel = os.path.relpath(self.file_info.target_file_path, self.file_info.work_dir)
        prompt_output_path = prompt_enum.get_prompt_file_path(target_file_path_rel, self.magic_info)
        return FileUtil.read_file(prompt_output_path)

    @log_inout
    def is_same_prompt(self, prompt_enum: PromptEnum = PromptEnum.INPUT) -> bool:
        # work_dirからの相対パス取得
        current_prompt = prompt_enum.get_current_prompt(self.magic_info)
        current_prompt = current_prompt.strip()
        past_prompt = self.load_prompt(prompt_enum)
        past_prompt = past_prompt.strip()

        log("current_prompt(末尾100文字)=\n%s", current_prompt[-100:])
        log("past_prompt(末尾100文字)=\n%s", past_prompt[-100:])
        return current_prompt == past_prompt

    def __str__(self) -> str:
        return f"PromptManager({self.magic_info.description})"

    def __repr__(self) -> str:
        return self.__str__()
