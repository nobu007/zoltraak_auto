import os
import re
from enum import Enum

from zoltraak.schema.schema import FileInfo, MagicInfo
from zoltraak.utils.file_util import FileUtil
from zoltraak.utils.log_util import log, log_e, log_inout


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

    def set_current_prompt(self, prompt: str, magic_info: MagicInfo) -> None:
        current_prompt_attr = f"prompt{self.value}"
        log("current_prompt_attr=%s", current_prompt_attr)
        setattr(magic_info, current_prompt_attr, prompt)

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
        log("プロンプトを保存しました↓ %s:\n%s", prompt_enum, prompt_output_path)

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

    @log_inout
    def prepare_prompt_final(self) -> str:
        """
        prompt_finalを生成してMagicInfoに反映する関数
        利用するグリモアはMagicInfoに展開済みの前提

        設計： 下記を全て反映したプロンプトを作成する
        - canonical_name(=source_org)
        - プロンプト(ユーザ要求 or ユーザ要求記述書)
        - コンテキスト(プロンプトに含める設計)
        - グリモア(compiler, formatter)
        """
        magic_info = self.magic_info
        compiler_path = magic_info.get_compiler_path()
        formatter_path = magic_info.get_formatter_path()
        language = magic_info.language

        prompt_final = self.create_prompt(
            magic_info.prompt_goal, compiler_path, formatter_path, language
        )  # プロンプトを作成
        log("prompt_final=\n%s\n...\n%s", prompt_final[:50], prompt_final[-5:])
        magic_info.prompt_final = prompt_final
        return prompt_final

    @log_inout
    def create_prompt(self, goal_prompt: str, compiler_path: str, formatter_path: str, language: str):
        """
        LLMへの最終的なプロンプト(prompt_final)を生成を作成する関数

        Returns:
            str: 作成されたプロンプト
        """

        prompt_final = goal_prompt
        if os.path.isfile(compiler_path):
            # コンパイラが存在する場合、コンパイラベースでプロンプトを取得
            prompt_final = FileUtil.read_grimoire(compiler_path, goal_prompt, language)
            prompt_final += "\n\n"
        if os.path.exists(formatter_path):
            prompt_final = self.apply_fomatter(prompt_final, formatter_path, language)

        # destiny_content
        destiny_content = FileUtil.read_file(self.file_info.destiny_file_path)
        prompt_final = (
            "#### 前提コンテキスト(この内容は重要ではないですが、緩く全体的な判断に活用してください) ####\n"
            + destiny_content
            + "#### 前提コンテキスト終了 ####\n\n"
            + prompt_final
        )
        log("len(prompt_final)=%d", len(prompt_final))

        return prompt_final

    @log_inout
    def apply_fomatter(self, final_prompt: str, formatter_path: str, language: str):
        modified_prompt = final_prompt
        if formatter_path != "" and language is not None:
            formatter_prompt = self.get_formatter_prompt(formatter_path, language)
            # 多言語のフォーマッターの場合、言語指定を強調する
            if not formatter_path.endswith("_lang.md"):
                try:
                    find_word = "## Output Language"
                    start_index = final_prompt.rindex(find_word)
                    end_index = start_index + len(find_word) + 1  # TODO: もっと正確に探す
                    modified_prompt = (
                        final_prompt[:start_index]
                        + "\n- Follow the format defined in the format section. DO NOT output the section itself."
                        + formatter_prompt
                        + final_prompt[end_index:]
                    )  # 言語指定の強調前出しでサンドイッチにしてみる。
                except ValueError:
                    # rindexが取れなかった場合の処理
                    final_prompt = (
                        "\n- Follow the format defined in the format section. DO NOT output the section itself."
                        + final_prompt
                    )

            elif re.match("(english|英語|en)", language.lower()):
                modified_prompt = (
                    final_prompt + formatter_prompt
                )  # 英語指示が「デフォルト言語指示」と混同されやすく、効きがやたら悪いので英語の場合は挟み撃ちにする
        log("modified_prompt[:100]=" + modified_prompt[:100])
        return modified_prompt

    @log_inout
    def get_formatter_prompt(self, formatter_path: str, language: str | None = None):
        """
        フォーマッタのプロンプトを取得する関数

        Args:
            formatter_path (str): フォーマッタのパス

        Returns:
            str: フォーマッタの内容
        """
        if formatter_path is None:  # フォーマッタパスが指定されていない場合
            formatter_prompt = ""  # - フォーマッタを空文字列に設定
        elif os.path.exists(formatter_path):  # -- フォーマッタファイルが存在する場合
            formatter_prompt = FileUtil.read_grimoire(formatter_path, language=language)
            if language and formatter_path.endswith("_lang.md"):
                formatter_prompt += f"""\n- You must output everything including code block and diagrams,
                according to the previous instructions, but make sure you write your response in {language}.

                \n## Output Language\n- You must generate your response using {language},
                which is the language of the formatter just above this sentence."""
        else:  # -- フォーマッタファイルが存在しない場合
            log_e(f"フォーマッタファイル {formatter_path} が見つかりません。")  # --- エラーメッセージを表示
            formatter_prompt = ""  # --- フォーマッタを空文字列に設定

        return formatter_prompt

    def __str__(self) -> str:
        return f"PromptManager({self.magic_info.description})"

    def __repr__(self) -> str:
        return self.__str__()
