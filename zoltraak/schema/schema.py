from __future__ import annotations

import hashlib
import os
from enum import Enum

from pydantic import BaseModel, Field

from zoltraak import settings


class SourceTargetSet(BaseModel):
    source_file_path: str = Field(default="", description="source_file_path")
    target_file_path: str = Field(default="", description="target_file_path")
    context_file_path: str = Field(default="", description="context_file_path")

    def __str__(self):
        return self.__repr__()

    def __repr__(self) -> str:
        return f"""SourceTargetSet
    source_file_path: {self.source_file_path}
    target_file_path: {self.target_file_path}
    context_file_path: {self.context_file_path}
  """


class MagicMode(str, Enum):
    GRIMOIRE_ONLY = "grimoire_only"  # プロンプト指定なしでグリモアのみ指定
    GRIMOIRE_AND_PROMPT = "grimoire_and_prompt"  # グリモア＋プロンプト
    PROMPT_ONLY = "prompt_only"  # プロンプト（グリモアなし）
    SEARCH_GRIMOIRE = "search_grimoire"  # 最適なグリモアを検索
    ZOLTRAAK_LEGACY = "zoltraak_legacy"  # オリジナルのzoltraakを模擬するモード（デバッグ用）

    def __str__(self):
        return self.value

    def __repr__(self) -> str:
        return self.value

    @staticmethod
    def get_description():
        description_list = ["グリモアの利用方法を指定します。"]
        for i, mode in enumerate(MagicMode):
            description_list.append(f"  {i}: " + str(mode))
        return "\n".join(description_list)


# next()メソッドを使って次のレイヤを取得するためのリスト
MAGIC_LAYER_ORDER = []


class MagicLayer(str, Enum):
    LAYER_1_REQUEST_GEN = "layer_1_request_gen"  # 生のprompt => ユーザ要求記述書
    LAYER_2_STRUCTURE_GEN = "layer_2_structure_gen"  # 生のprompt => ファイル構造定義書
    LAYER_2_1_AFFECTED_FILE_LIST_GEN = (
        "layer_2_1_affected_file_list_gen"  # ユーザ要求記述書 => 影響を受けるファイルリスト
    )
    LAYER_3_REQUIREMENT_GEN = "layer_3_requirement_gen"  # ユーザ要求記述書 and ファイル構造定義書 => 要件定義書
    LAYER_4_REQUIREMENT_GEN = "layer_4_requirement_gen"  # 要件定義書 => 要件定義書(requirements)
    LAYER_5_CODE_GEN = "layer_5_code_gen"  # 要件定義書(requirements) => Pythonコード（ファイル生成用）＋最終コード
    LAYER_5_1_DEPENDENCY_GEN = "layer_5_1_dependency_gen"  # 最終コード => 依存関係情報
    LAYER_6_CODEBASE_GEN = "layer_6_codebase_gen"  # 最終コード => コードベース
    LAYER_7_INFO_STRUCTURE_GEN = "layer_7_info_structure_gen"  # コードベース => 情報構造体(個別)
    LAYER_8_INFO_STRUCTURE_GEN = "layer_8_info_structure_gen"  # 情報構造体(個別) => 情報構造体
    LAYER_9_CODE_GEN_FINAL = "layer_9_code_gen_final"  #  情報構造体 => 最終コード（再作成）
    LAYER_10_MD_GEN_FINAL = "layer_10_md_gen_final"  #  情報構造体 => 最終マークダウン（再作成）
    LAYER_11_CLEAN_UP = "layer_11_clean_up"  # ファイル構造定義書 => 不要ファイル削除

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return self.value.replace("layer_", "")  # => 1_request_gen

    def level(self):
        level_str = self.value.replace("layer_", "")
        parts = level_str.split("_")
        if len(parts) > 1:
            layer_level_str = parts[0]  # layer_N_XXのNを取得
        else:
            error_message = f"Invalid MagicLayer value: {self.value}"
            raise ValueError(error_message)
        return int(layer_level_str)

    def next(self) -> MagicLayer | None:
        # 次のレベルのレイヤを返す
        current_index = MAGIC_LAYER_ORDER.index(self)
        next_index = current_index + 1
        if next_index <= len(MAGIC_LAYER_ORDER) + 1:
            return MAGIC_LAYER_ORDER[next_index]
        return None

    @staticmethod
    def get_description():
        description_list = [
            f"グリモアの起動レイヤを指定します。\n例えば「{MagicLayer.LAYER_5_CODE_GEN}」でコード生成から実行します。"
        ]
        for i, layer in enumerate(MagicLayer):
            level = i + 1
            description_list.append(f"  {level}: " + layer.__repr__())
        return "\n".join(description_list)

    @staticmethod
    def new(magic_layer_str: str):
        # 文字列からMagicLayerを取得する
        for layer in MagicLayer:
            if magic_layer_str in layer.value:
                # レイヤが見つかったケース
                return layer
        # レイヤが見つからなかったケースのデフォルト値
        return MagicLayer.LAYER_4_REQUIREMENT_GEN


# MagicLayer定義が完了後にMAGIC_LAYER_ORDERを作成
MAGIC_LAYER_ORDER = list(MagicLayer)


class ZoltraakParams(BaseModel):
    # input: str = Field(default="", description="対変換対象のMarkdownまたはテキスト(分かりづらいので廃止)")
    output_dir: str = Field(default="generated", description="生成されたPythonファイルの出力ディレクトリ")
    prompt: str = Field(default="", description="追加のプロンプト情報")
    compiler: str = Field(default="", description="コンパイラー（要件定義書のテンプレート）")
    architect: str = Field(
        default="architect_claude.md", description="対変換対象のarchitectファイルのパスまたはテキスト"
    )
    formatter: str = Field(default="", description="対変換対象のMarkdownファイルのパスまたはテキスト")
    language: str = Field(default="", description="対出力言語を指定")
    model_name: str = Field(default="", description="使用するモデルの名前")
    canonical_name: str = Field(default="zoltraak", description="正規名称(最初のinputのMarkdownファイル名: xx.md->xx）")
    magic_mode: str = Field(default="", description="グリモアの利用方法")
    magic_layer: str = Field(default="", description="グリモアの起動レイヤ")
    magic_layer_end: str = Field(default="", description="グリモアの終了レイヤ")
    eternal_intent: str = Field(default="", description="全レイヤで共通不変の永続的な作業指示")

    def get_zoltraak_command(self):
        cmd = "zoltraak"
        for field, value in self:
            if value:
                cmd += f' --{field} "{value}"'
        print("get_zoltraak_command cmd=", cmd)
        return cmd


DEFAULT_CANONICAL_NAME = "zoltraak.md"
DEFAULT_COMPILER = "general_prompt.md"
DEFAULT_DESTINY_FILE = "DESTINY.md"
DEFAULT_PROMPT_FILE = "PROMPT.md"
DEFAULT_REQUEST_FILE = "REQUEST.md"
DEFAULT_STRUCTURE_FILE = "STRUCTURE.md"
DEFAULT_MD_FILE = "ARCHITECTURE.md"
DEFAULT_PY_FILE = "ARCHITECTURE.py"
DEFAULT_DEPENDENCY_FILE = "DEPENDENCY.md"
EMPTY_CONTEXT_FILE = "EMPTY_CONTEXT.md"


class FileInfo(BaseModel):
    # 識別子
    canonical_name: str = Field(
        default="zoltraak", description="対象のファイル群をシステム全体で一意に識別するための標準的な名前"
    )

    # Input/Outputファイル
    destiny_file_path: str = Field(
        default=os.path.abspath(DEFAULT_DESTINY_FILE),
        description="不変のユーザ要求(別名: eternal_intent)を保存するファイル (絶対パス)",
    )
    prompt_file_path: str = Field(
        default=os.path.abspath(DEFAULT_PROMPT_FILE),
        description="ユーザ要求を保存するファイル(絶対パス)",
    )
    request_file_path: str = Field(
        default=os.path.abspath(DEFAULT_REQUEST_FILE),
        description="ユーザ要求記述書のmdファイル(絶対パス)",
    )
    structure_file_path: str = Field(
        default=os.path.abspath(DEFAULT_STRUCTURE_FILE),
        description="ファイル構造定義書のファイル(絶対パス)",
    )
    md_file_path: str = Field(
        default=os.path.abspath(DEFAULT_MD_FILE),
        description="要件定義書のmdファイル(絶対パス)",
    )
    py_file_path: str = Field(default=os.path.abspath(DEFAULT_PY_FILE), description="処理対象のpyファイル(絶対パス)")
    dependency_file_path: str = Field(
        default=os.path.abspath(DEFAULT_DEPENDENCY_FILE),
        description="依存関係情報を保存するファイル(絶対パス)",
    )

    # ルートディレクトリ
    work_dir: str = Field(default=os.getcwd(), description="作業ディレクトリ")
    target_dir: str = Field(default="./generated", description="出力先のルートディレクトリ")
    final_dir: str = Field(default="./generated_final", description="出力先のルートディレクトリ(修正版)")
    py_target_dir: str = Field(default="./generated/xxxx", description="python出力先のディレクトリ")
    past_dir: str = Field(default="./past", description="過去の出力先のルートディレクトリ")
    past_source_dir: str = Field(default="./past/source", description="過去のソースフォルダ")
    past_target_dir: str = Field(default="./past/target", description="過去の出力先ファイルフォルダ")
    past_context_dir: str = Field(default="./past/context", description="過去のコンテキストファイルフォルダ")
    prompt_dir: str = Field(default="./prompt", description="利用したプロンプト離籍のルートディレクトリ")

    # 処理対象ファイル(convert source => targetに利用)
    source_file_path: str = Field(default=DEFAULT_REQUEST_FILE, description="ソースファイルパス(絶対パス)")
    target_file_path: str = Field(default=DEFAULT_MD_FILE, description="処理対象のファイルパス(絶対パス)")
    context_file_path: str = Field(default=EMPTY_CONTEXT_FILE, description="コンテキストファイルパス(絶対パス)")
    target_file_name: str = Field(default=DEFAULT_MD_FILE, description="処理対象のファイル名")
    source_file_name: str = Field(default=DEFAULT_REQUEST_FILE, description="ソースファイル名")
    context_file_name: str = Field(default=EMPTY_CONTEXT_FILE, description="コンテキストのファイル名")
    past_source_file_path: str = Field(
        default="./past/source/" + DEFAULT_REQUEST_FILE, description="過去のソースファイル(絶対パス)"
    )
    past_target_file_path: str = Field(
        default="./past/target/" + DEFAULT_MD_FILE, description="過去の出力先ファイル(絶対パス)"
    )
    past_context_file_path: str = Field(
        default="./past/context/" + EMPTY_CONTEXT_FILE, description="過去のコンテキストファイル(絶対パス)"
    )

    # 結果ファイルパス
    output_file_path: str = Field(default="", description="直近の１変換の結果ファイルパス(絶対パス)")
    output_file_path_history: str = Field(default="", description="連続変換の結果ファイルパス履歴(絶対パス)")
    final_output_file_path: str = Field(default="", description="最終結果のファイルパス(絶対パス)")

    # その他
    source_hash: str = Field(default="1", description="ソースファイルのハッシュ値")
    target_hash: str = Field(default="2", description="出力先ファイルのハッシュ値")
    context_hash: str = Field(default="10", description="コンテキストファイルのハッシュ値")
    past_source_hash: str = Field(default="3", description="過去のソースファイルのハッシュ値")
    past_target_hash: str = Field(default="4", description="過去の出力先ファイルのハッシュ値")
    past_context_hash: str = Field(default="11", description="過去のコンテキストファイルのハッシュ値")

    def update_work_dir(self, new_work_dir: str = ""):
        if not new_work_dir:
            new_work_dir = os.getcwd()
        self.work_dir = os.path.abspath(new_work_dir)
        self.past_dir = os.path.abspath(os.path.join(self.work_dir, "past"))
        self.prompt_dir = os.path.abspath(os.path.join(self.work_dir, "prompt"))
        self.update_path_abs()

    def update(self, canonical_name: str = ""):
        if not canonical_name:
            canonical_name = self.canonical_name
        else:
            self.canonical_name = canonical_name
        self.update_canonical_name(canonical_name)
        self.update_path_abs()
        self.update_source_target_past()
        self.update_hash()

    def update_canonical_name(self, canonical_name: str):
        self.destiny_file_path = "destiny_" + canonical_name + ".md"
        self.prompt_file_path = "prompt_" + canonical_name + ".md"
        self.request_file_path = "request_" + canonical_name + ".md"
        self.structure_file_path = "structure_" + canonical_name + ".md"
        self.md_file_path = canonical_name + ".md"
        self.py_file_path = canonical_name + ".py"
        self.dependency_file_path = "dependency_" + canonical_name + ".dot"

    def update_path_abs(self):
        if self.destiny_file_path:
            self.destiny_file_path = os.path.abspath(self.destiny_file_path)
        if self.prompt_file_path:
            self.prompt_file_path = os.path.abspath(self.prompt_file_path)
        if self.request_file_path:
            self.request_file_path = os.path.abspath(self.request_file_path)
        if self.structure_file_path:
            self.structure_file_path = os.path.abspath(self.structure_file_path)
        if self.md_file_path:
            self.md_file_path = os.path.abspath(self.md_file_path)
        if self.py_file_path:
            self.py_file_path = os.path.abspath(self.py_file_path)
        if self.dependency_file_path:
            self.dependency_file_path = os.path.abspath(self.dependency_file_path)

    def update_source_target(self, source_file_path, target_file_path, context_file_path=EMPTY_CONTEXT_FILE):
        # source_file_path, source_file_path を更新する処理(path系のトリガー)

        # full path
        self.source_file_path = os.path.abspath(source_file_path)
        self.target_file_path = os.path.abspath(target_file_path)
        self.context_file_path = os.path.abspath(context_file_path)

        # file name
        self.source_file_name = os.path.basename(source_file_path)
        self.target_file_name = os.path.basename(target_file_path)
        self.context_file_name = os.path.basename(context_file_path)

        # mkdir
        os.makedirs(os.path.dirname(self.source_file_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.target_file_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.context_file_path), exist_ok=True)

        # past source and target
        self.update_source_target_past()

        # output_file_path
        if not self.output_file_path_history:
            self.output_file_path_history = "(src)" + self.source_file_name

        # hash
        self.update_hash()

    def update_source_target_past(self):
        # work_dirからの相対パス取得
        source_file_path_rel = os.path.relpath(self.source_file_path, self.work_dir)
        target_file_path_rel = os.path.relpath(self.target_file_path, self.work_dir)
        context_file_path_rel = os.path.relpath(self.context_file_path, self.work_dir)

        # past_path更新(絶対パス)
        self.past_source_file_path = os.path.abspath(os.path.join(self.past_dir, "source", source_file_path_rel))
        self.past_target_file_path = os.path.abspath(os.path.join(self.past_dir, "target", target_file_path_rel))
        self.past_context_file_path = os.path.abspath(os.path.join(self.past_dir, "context", context_file_path_rel))

        # past_dir更新
        self.past_source_dir = os.path.dirname(self.past_source_file_path)
        self.past_target_dir = os.path.dirname(self.past_target_file_path)
        self.past_context_dir = os.path.dirname(self.past_context_file_path)

        # past_dir作成
        os.makedirs(self.past_source_dir, exist_ok=True)
        os.makedirs(self.past_target_dir, exist_ok=True)
        os.makedirs(self.past_context_dir, exist_ok=True)

    def update_hash(self):
        self.source_hash = self.calculate_file_hash(self.source_file_path)
        self.target_hash = self.calculate_file_hash(self.target_file_path)
        self.context_hash = self.calculate_file_hash(self.context_file_path)
        self.past_source_hash = self.calculate_file_hash(self.past_source_file_path)
        self.past_target_hash = self.calculate_file_hash(self.past_target_file_path)
        self.past_context_hash = self.calculate_file_hash(self.past_context_file_path)

    def add_output_file_path(self, output_file_path: str):
        self.output_file_path = os.path.abspath(output_file_path)
        self.output_file_path_history += f"\n{self.output_file_path}"

    def is_same_hash_source_target(self) -> bool:
        if not self.source_hash:
            return False
        if not self.target_hash:
            return False
        return self.source_hash == self.target_hash

    def __str__(self) -> str:
        str_list = []
        for key, value in self.model_dump().items():
            sv = str(value)
            str_list.append(f"  {key}={sv}")
        return "\n\n".join(str_list)

    def __repr__(self) -> str:
        return self.__str__()

    @staticmethod
    def calculate_file_hash(file_path) -> str:
        if os.path.isfile(file_path):
            with open(file_path, "rb") as file:
                content = file.read()
                return hashlib.sha256(content).hexdigest()
        return ""


class MagicInfo(BaseModel):
    # コア情報
    magic_mode: MagicMode = Field(default=MagicMode.PROMPT_ONLY, description="実行モード")
    magic_layer: MagicLayer = Field(default=MagicLayer.LAYER_1_REQUEST_GEN, description="グリモアの実行中レイヤ")
    magic_layer_end: MagicLayer = Field(default=MagicLayer.LAYER_5_CODE_GEN, description="グリモアの終了レイヤ")
    model_name: str = Field(default=settings.model_name, description="使用するLLMモデルの名前")
    prompt_input: str = Field(
        default="""
        zoltraakシステムは曖昧なユーザー入力を、ユーザ要求記述書 => 要件定義書 => Pythonコードと段階的に詳細化します。
        このシステムの情報を提供しますので作業指示に従ってください。
        """,
        description="ユーザ入力を保持するためのプロンプト(cli.pyで-iまたは引数なしで指定されたオリジナルを保持)",
    )
    prompt_match_rate: str = Field(
        default="",
        description="既存のターゲットファイルと現在のソースファイルの適合度を取得するプロンプト(履歴用)",
    )
    prompt_diff_order: str = Field(
        default="",
        description="既存のターゲットファイルに対して、どのような差分を適用するべきかを指示するプロンプト(履歴用)",
    )
    prompt_diff: str = Field(
        default="",
        description="既存のターゲットファイルに対して、差分を取得するためのプロンプト(履歴用)",
    )
    prompt_apply: str = Field(
        default="",
        description="既存のターゲットファイルに対して、差分を適用するためのプロンプト(履歴用)",
    )
    prompt_goal: str = Field(
        default="",
        description="ターゲットファイルを新規作成するときのゴール(履歴用)",
    )
    prompt_final: str = Field(
        default="",
        description="ターゲットファイルを新規生成するために最終的に使われた(履歴用)",
    )

    # grimoire関連
    current_grimoire_name: str = Field(
        default="dev_obj.md", description="現在実行中のグリモア名(generate_xx関数の先頭で設定)"
    )
    description: str = Field(
        default="汎用魔法式を展開します", description="現在実行中の説明(generate_xx関数の先頭で設定)"
    )
    grimoire_compiler: str = Field(
        default=DEFAULT_COMPILER, description="使用するグリモアコンパイラのファイル名(未使用なら空文字)"
    )
    grimoire_architect: str = Field(
        default="architect_claude.md", description="使用するグリモアアーキテクトのファイル名(未使用なら空文字)"
    )
    grimoire_formatter: str = Field(
        default="md_comment.md", description="使用するグリモアフォーマッタのファイル名(未使用なら空文字)"
    )

    # file関連
    file_info: FileInfo = Field(default=FileInfo(), description="入出力ファイル情報")

    # その他
    is_success: bool = Field(default=True, description="魔法式の成否")
    success_message: str = Field(default="魔法式の構築が完了しました。", description="グリモア成功時のメッセージ")
    error_message: str = Field(
        default="魔法式の構築中にエラーが発生しました。", description="グリモア失敗時のメッセージ"
    )
    language: str = Field(default="", description="汎用言語指定(現状ではgrimoire_formatterに影響)")
    history_info: str = Field(default="", description="スキップ有無や新規/追加などの履歴(デバッグ用)")

    is_debug: bool = Field(default=True, description="デバッグモード(グリモア情報を逐次出力)")
    is_async: bool = Field(default=False, description="非同期モード(一部の同期処理をスキップする)")
    score: float = Field(default=1.0, description="スコア(0.0:悪い、1.0:良い)")

    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.file_info.update()

    def get_compiler_path(self, grimoire_compiler: str = ""):
        if grimoire_compiler == "":
            grimoire_compiler = self.grimoire_compiler
        return os.path.join(settings.compiler_dir, grimoire_compiler)

    def get_architect_path(self):
        return os.path.join(settings.architects_dir, self.grimoire_architect)

    def get_formatter_path(self):
        return os.path.join(settings.formatter_dir, self.grimoire_formatter)


class MagicWorkflowInfo(BaseModel):
    # 履歴
    magic_info_list: list[MagicInfo] = Field(default_factory=list, description="workflowで実行したMagicInfoのコピー")
