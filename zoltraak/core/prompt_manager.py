import os
import re
from dataclasses import dataclass
from enum import Enum

import pandas as pd

from zoltraak.schema.schema import MagicInfo, MagicLayer, MagicMode
from zoltraak.utils.diff_util import DiffUtil
from zoltraak.utils.file_util import FileUtil
from zoltraak.utils.log_util import log, log_e, log_inout


@dataclass
class PromptParams:
    prompt: str = ""
    language: str = ""
    compiler_path: str = ""
    formatter_path: str = ""
    architect_path: str = ""
    canonical_name: str = ""
    source_file_name: str = ""
    source_file_path: str = ""
    source_content: str = ""
    target_file_path: str = ""
    target_file_name: str = ""
    target_content: str = ""
    context_file_path: str = ""
    context_file_name: str = ""
    context_content: str = ""
    requirements_content: str = ""
    destiny_file_path: str = ""

    def __init__(self, magic_info: MagicInfo):
        file_info = magic_info.file_info

        self.prompt = magic_info.prompt_goal
        self.language = magic_info.language
        self.compiler_path = magic_info.get_compiler_path()
        self.formatter_path = magic_info.get_formatter_path()
        self.architect_path = magic_info.get_architect_path()
        self.canonical_name = magic_info.file_info.canonical_name
        self.source_file_name = file_info.source_file_name
        self.source_file_path = file_info.source_file_path
        self.source_content = FileUtil.read_file(file_info.source_file_path)
        self.target_file_path = file_info.target_file_path
        self.target_file_name = file_info.target_file_name
        self.target_content = FileUtil.read_file(file_info.target_file_path)
        self.context_file_path = file_info.context_file_path
        self.context_file_name = file_info.context_file_name
        self.context_content = FileUtil.read_file(file_info.context_file_path)
        self.requirements_content = FileUtil.read_file(file_info.md_file_path)  # 要求仕様書
        self.destiny_file_path = magic_info.file_info.destiny_file_path

    def to_replace_map(self):
        """PromptParamsのフィールドを辞書に変換する
        例） {"prompt": prompt, "language": language, ...}
        """
        return {f.name: getattr(self, f.name) for f in self.__dataclass_fields__.values()}


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
    def __init__(self):
        self.df = pd.DataFrame()
        self.prompt_len_list = []
        self.score_list = []
        self.prompt_output_path_list = []
        self.prompt_head_list = []
        self.prompt_tail_list = []

    @log_inout
    def save_prompts(self, magic_info: MagicInfo) -> None:
        # work_dirからの相対パス取得
        target_file_path_rel = os.path.relpath(magic_info.file_info.target_file_path, magic_info.file_info.work_dir)

        # promptの保存先パス取得
        for prompt_enum in PromptEnum:
            self.save_prompt(magic_info, prompt_enum.get_current_prompt(magic_info), target_file_path_rel, prompt_enum)

    @log_inout
    def save_prompt(
        self, magic_info: MagicInfo, prompt: str, target_file_path_rel: str, prompt_enum: PromptEnum = PromptEnum.INPUT
    ) -> None:
        prompt_output_path = prompt_enum.get_prompt_file_path(target_file_path_rel, magic_info)

        # フォルダがない場合は作成
        os.makedirs(os.path.dirname(prompt_output_path), exist_ok=True)

        # プロンプトを保存
        FileUtil.write_prompt(prompt, prompt_output_path)
        log("プロンプトを保存しました↓ %s:\n%s", prompt_enum, prompt_output_path)

        # csvに保存
        prompt_str = str(prompt).strip()
        prompt_len = len(prompt_str)
        if prompt_len > 0:
            self.prompt_len_list.append(prompt_len)
            self.score_list.append(magic_info.score)
            self.prompt_output_path_list.append(prompt_output_path)
            self.prompt_head_list.append(prompt_str[:100])
            self.prompt_tail_list.append(prompt_str[-100:])
            self.df = pd.DataFrame(
                data={
                    "prompt_len": self.prompt_len_list,
                    "score": self.score_list,
                    "prompt_output_path": self.prompt_output_path_list,
                    "prompt_head": self.prompt_head_list,
                    "prompt_tail": self.prompt_tail_list,
                }
            )
            self.df.to_csv("prompt.csv")

    @log_inout
    def load_prompt(self, magic_info: MagicInfo, prompt_enum: PromptEnum = PromptEnum.INPUT) -> str:
        # work_dirからの相対パス取得
        target_file_path_rel = os.path.relpath(magic_info.file_info.target_file_path, magic_info.file_info.work_dir)
        prompt_output_path = prompt_enum.get_prompt_file_path(target_file_path_rel, magic_info)
        return FileUtil.read_file(prompt_output_path)

    @log_inout
    def is_same_prompt(self, magic_info: MagicInfo, prompt_enum: PromptEnum = PromptEnum.INPUT) -> bool:
        # work_dirからの相対パス取得
        current_prompt = prompt_enum.get_current_prompt(magic_info)
        past_prompt = self.load_prompt(magic_info, prompt_enum)

        log("PromptEnum=" + prompt_enum + " current_prompt(末尾100文字)=\n%s", current_prompt[-100:])
        log("PromptEnum=" + prompt_enum + " past_prompt(末尾100文字)=\n%s", past_prompt[-100:])
        diff_content = DiffUtil.diff0_ignore_space(current_prompt, past_prompt)

        if diff_content.strip() == "":
            log("PromptEnum=" + prompt_enum + " プロンプトが同じです")
            return True
        log("PromptEnum=" + prompt_enum + " プロンプトが異なります diff=\n%s", diff_content)
        return False

    @log_inout
    def show_diff_prompt(self, magic_info: MagicInfo, prompt_enum: PromptEnum = PromptEnum.INPUT) -> None:
        # work_dirからの相対パス取得
        current_prompt = prompt_enum.get_current_prompt(magic_info)
        past_prompt = self.load_prompt(magic_info, prompt_enum)
        log(DiffUtil.diff0_ignore_space(current_prompt, past_prompt))

    @log_inout
    def prepare_prompt_final(self, magic_info: MagicInfo) -> str:
        """
        prompt_finalを生成してMagicInfoに反映する関数
        利用するグリモアはMagicInfoに展開済みの前提

        設計： 下記を全て反映したプロンプトを作成する
        - canonical_name(=source_org)
        - プロンプト(ユーザ要求 or ユーザ要求記述書)
        - コンテキスト(プロンプトに含める設計)
        - グリモア(compiler, formatter, architect)
        """
        # PromptParamsを作成
        prompt_params = PromptParams(magic_info=magic_info)
        if magic_info.magic_layer == MagicLayer.LAYER_5_CODE_GEN and magic_info.magic_mode == MagicMode.ZOLTRAAK_LEGACY:
            # コード生成時はarchitectを利用する
            prompt_final = self.create_prompt_architect(prompt_params)
        else:
            # 通常はcompilerを利用する
            prompt_final = self.create_prompt(prompt_params)
        log("prompt_final=\n%s\n...\n%s", prompt_final[:50], prompt_final[-5:])
        magic_info.prompt_final = prompt_final
        return prompt_final

    @log_inout
    def create_prompt(self, params: PromptParams):
        """
        LLMへの最終的なプロンプト(prompt_final)を生成を作成する関数(compiler版)

        Returns:
            str: 作成されたプロンプト
        """

        prompt_final = params.prompt
        if os.path.isfile(params.compiler_path):
            # コンパイラが存在する場合、コンパイラベースでプロンプトを取得
            prompt_final = PromptManager.read_grimoire(params.compiler_path, params.to_replace_map())
            prompt_final += "\n\n"
        if os.path.exists(params.formatter_path):
            prompt_final = self.apply_fomatter(prompt_final, params.formatter_path, params.language)

        # destiny_content
        destiny_content = FileUtil.read_file(params.destiny_file_path)
        prompt_final = (
            "#### 前提コンテキスト(この内容は重要ではないですが、緩く全体的な判断に活用してください) ####\n"
            + destiny_content
            + "\n#### 前提コンテキスト終了 ####\n\n"
            + prompt_final
        )
        log("len(prompt_final)=%d", len(prompt_final))

        return prompt_final

    @log_inout
    def create_prompt_architect(self, params: PromptParams):
        """
        LLMへの最終的なプロンプト(prompt_final)を生成を作成する関数(architect版)

        Returns:
            str: 作成されたプロンプト
        """

        prompt_final = params.source_content
        if os.path.isfile(params.architect_path):
            # コンパイラが存在する場合、コンパイラベースでプロンプトを取得
            prompt_final = self.read_grimoire(file_path=params.architect_path, replace_map=params.to_replace_map())
            prompt_final += "\n\n"

        # destiny_content
        destiny_content = FileUtil.read_file(params.destiny_file_path)
        prompt_final = (
            "#### 前提コンテキスト(この内容は重要ではないですが、緩く全体的な判断に活用してください) ####\n"
            + destiny_content
            + "\n#### 前提コンテキスト終了 ####\n\n"
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
            replace_map = {"language": language}
            formatter_prompt = PromptManager.read_grimoire(file_path=formatter_path, replace_map=replace_map)
            if language and formatter_path.endswith("_lang.md"):
                formatter_prompt += f"""\n- You must output everything including code block and diagrams,
                according to the previous instructions, but make sure you write your response in {language}.

                \n## Output Language\n- You must generate your response using {language},
                which is the language of the formatter just above this sentence."""
        else:  # -- フォーマッタファイルが存在しない場合
            log_e(f"フォーマッタファイル {formatter_path} が見つかりません。")  # --- エラーメッセージを表示
            formatter_prompt = ""  # --- フォーマッタを空文字列に設定

        return formatter_prompt

    @staticmethod
    def read_grimoire(
        file_path: str,
        replace_map: dict[str, str] | None = None,
    ) -> str:
        # グリモアを読み込む
        content = FileUtil.read_file(file_path)

        # パターンを準備する
        def replacement(match):
            # マッチした3つのグループのうち、None以外のものを使用
            key = next(group for group in match.groups() if group is not None)
            return replace_map.get(key, match.group(0))

        # 一度の`re.sub`で全ての置換を行う
        # 各パターンを()でグループ化し、変数名も()でグループ化
        pattern = r"{{(\w+)}}|{(\w+)}|$$(\w+)$$"
        content = re.sub(pattern, replacement, content)

        # if replace_map:
        #     for key, value in replace_map.items():
        #         content = content.replace("{{" + key + "}}", value)
        #         content = content.replace("{" + key + "}", value)
        #         content = content.replace(f"[{key}]", value)
        log(f"read_grimoire content[:100]:\n {content[:100]}")
        return content

    def __str__(self) -> str:
        return "PromptManager"

    def __repr__(self) -> str:
        return self.__str__()
