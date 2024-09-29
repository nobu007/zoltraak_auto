import hashlib
import os
from enum import Enum

from pydantic import BaseModel, Field

from zoltraak import settings


class MagicMode(str, Enum):
    GRIMOIRE_ONLY = "grimoire_only"  # プロンプト指定なしでグリモアのみ指定
    GRIMOIRE_AND_PROMPT = "grimoire_and_prompt"  # グリモア＋プロンプト
    PROMPT_ONLY = "prompt_only"  # プロンプト（グリモアなし）
    SEARCH_GRIMOIRE = "search_grimoire"  # 最適なグリモアを検索

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


class MagicLayer(str, Enum):
    LAYER_1_REQUEST_GEN = "layer_1_request_gen"  # レイヤ１： 生のprompt => ユーザ要求記述書
    LAYER_2_REQUIREMENT_GEN = "layer_2_requirement_gen"  # レイヤ２： ユーザ要求記述書 => 要件定義書
    LAYER_3_CODE_GEN = "layer_3_code_gen"  # レイヤ３： 要件定義書 => コード

    def __str__(self):
        return self.value

    def __repr__(self) -> str:
        return self.value.split("_", 1)[1]  # => layer_1

    @staticmethod
    def get_description():
        description_list = ["グリモアの起動レイヤを指定します。例えばコード生成から再実行できます。"]
        for i, layer in enumerate(MagicLayer):
            description_list.append(f"  {i}: " + layer.__repr__())
        return "\n".join(description_list)


class ZoltraakParams(BaseModel):
    input: str = Field(default="", description="対変換対象のMarkdownファイルのパスまたはテキスト")
    output_dir: str = Field(default="generated", description="生成されたPythonファイルの出力ディレクトリ")
    prompt: str = Field(default="", description="追加のプロンプト情報")
    compiler: str = Field(default="", description="コンパイラー（要件定義書のテンプレート）")
    formatter: str = Field(default="", description="対変換対象のMarkdownファイルのパスまたはテキスト")
    language: str = Field(default="", description="対出力言語を指定")
    model_name: str = Field(default="", description="使用するモデルの名前")
    magic_mode: str = Field(default="", description="グリモアの利用方法")
    magic_layer: str = Field(default="", description="グリモアの起動レイヤ")

    # 以降は自動設定される項目(引数由来ではない)
    canonical_name: str = Field(
        default="zoltraak.md", description="作成対象の識別子(通常はinputのMarkdownファイル名: xx.md）"
    )

    def get_zoltraak_command(self):
        cmd = f"zoltraak {self.input}"
        if self.output_dir:
            cmd += f" --output-dir {self.output_dir}"
        if self.prompt:
            cmd += f" --prompt {self.prompt}"
        if self.compiler:
            cmd += f" --compiler {self.compiler}"
        if self.formatter:
            cmd += f" --formatter {self.formatter}"
        if self.language:
            cmd += f" --language {self.language}"
        if self.model_name:
            cmd += f" --model_name {self.model_name}"
        if self.model_name:
            cmd += f" --magic_mode {self.magic_mode}"
        if self.model_name:
            cmd += f" --magic_layer {self.magic_layer}"
        print("get_zoltraak_command cmd=", cmd)
        return cmd


DEFAULT_COMPILER = "general_prompt.md"
DEFAULT_PROMPT_FILE = "PROMPT.md"
DEFAULT_PRE_MD_FILE = "REQUEST.md"
DEFAULT_MD_FILE = "ARCHITECTURE.md"
DEFAULT_PY_FILE = "ARCHITECTURE.py"


class FileInfo(BaseModel):
    # 識別子
    canonical_name: str = Field(
        default="zoltraak", description="対象のファイル群をシステム全体で一意に識別するための標準的な名前"
    )

    # Input/Outputファイル
    prompt_file_path: str = Field(
        default=DEFAULT_PROMPT_FILE,
        description="ユーザ要求を保存するファイル(カレントからの相対パス or 絶対パス)",
    )
    prompt_file_path_abs: str = Field(
        default=os.path.abspath(DEFAULT_PROMPT_FILE),
        description="ユーザ要求を保存するファイル(絶対パス)",
    )
    pre_md_file_path: str = Field(
        default=DEFAULT_PRE_MD_FILE,
        description="ユーザ要求記述書のmdファイル(カレントからの相対パス or grimoires_dirからの相対パス or 絶対パス)",
    )
    pre_md_file_path_abs: str = Field(
        default=os.path.abspath(DEFAULT_PRE_MD_FILE),
        description="ユーザ要求記述書のmdファイル(絶対パス)",
    )
    md_file_path: str = Field(
        default=DEFAULT_MD_FILE,
        description="要件定義書のmdファイル(カレントからの相対パス or grimoires_dirからの相対パス or 絶対パス)",
    )
    md_file_path_abs: str = Field(
        default=os.path.abspath(DEFAULT_MD_FILE),
        description="要件定義書のmdファイル(絶対パス)",
    )
    py_file_path: str = Field(
        default=DEFAULT_PY_FILE, description="処理対象のpyファイル(カレントからの相対パス or 絶対パス)"
    )
    py_file_path_abs: str = Field(
        default=os.path.abspath(DEFAULT_PY_FILE), description="処理対象のpyファイル(絶対パス)"
    )

    # 処理対象ファイル(convert source => target)
    source_file_path: str = Field(default=DEFAULT_PRE_MD_FILE, description="ソースファイルパス(絶対パス)")
    target_file_path: str = Field(default=DEFAULT_MD_FILE, description="処理対象のファイルパス(絶対パス)")
    past_source_file_path: str = Field(default="", description="過去のソースファイル")
    past_target_file_path: str = Field(default="", description="過去の出力先ファイル(絶対パス)")
    past_source_folder: str = Field(default="past_md_files", description="過去のソースフォルダ")
    past_target_folder: str = Field(default="past_py_files", description="過去の出力先ファイルフォルダ")
    target_dir: str = Field(default="./output", description="出力先のディレクトリ")

    # その他
    source_hash: str = Field(default="1", description="ソースファイルのハッシュ値")
    target_hash: str = Field(default="2", description="出力先ファイルのハッシュ値")
    past_source_hash: str = Field(default="3", description="過去のソースファイルのハッシュ値")
    past_target_hash: str = Field(default="4", description="過去の出力先ファイルのハッシュ値")

    def update(self):
        self.update_path_abs()
        self.update_hash()

    def update_path_abs(self):
        self.pre_md_file_path_abs = os.path.abspath(self.pre_md_file_path)
        self.md_file_path_abs = os.path.abspath(self.md_file_path)
        self.py_file_path_abs = os.path.abspath(self.py_file_path)

    def update_source_target(self, source_file_path, target_file_path):
        self.source_file_path = source_file_path
        self.target_file_path = target_file_path

    def update_source_target_past(self, past_source_folder, past_target_folder):
        self.past_source_folder = past_source_folder
        self.past_target_folder = past_target_folder
        os.makedirs(past_source_folder, exist_ok=True)
        os.makedirs(past_target_folder, exist_ok=True)

    def update_hash(self):
        self.source_hash = self.calculate_file_hash(self.source_file_path)
        self.target_hash = self.calculate_file_hash(self.target_file_path)
        self.past_source_hash = self.calculate_file_hash(self.past_source_file_path)
        self.past_target_hash = self.calculate_file_hash(self.past_target_file_path)

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
    magic_layer: MagicLayer = Field(default=MagicLayer.LAYER_1_REQUEST_GEN, description="実行モード")
    model_name: str = Field(default=settings.model_name, description="使用するLLMモデルの名前")
    prompt: str = Field(
        default="""
        zoltraakシステムは曖昧なユーザー入力を、ユーザ要求記述書 => 要件定義書 => Pythonコードと段階的に詳細化します。
        このシステムの情報を提供しますので作業指示に従ってください。
        """,
        description="使用するグリモアのプロンプト",
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
    success_message: str = Field(default="魔法式の構築が完了しました。", description="グリモア成功時のメッセージ")
    error_message: str = Field(
        default="魔法式の構築中にエラーが発生しました。", description="グリモア失敗時のメッセージ"
    )
    language: str = Field(default="", description="汎用言語指定(現状ではgrimoire_formatterに影響)")
    is_debug: bool = Field(default=True, description="デバッグモード(グリモア情報を逐次出力)")

    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

        self.md_file_path_abs = os.path.abspath(self.md_file_path)
        self.py_file_path_abs = os.path.abspath(self.py_file_path)
        return self

    def get_compiler_path(self):
        return os.path.join(settings.compiler_dir, self.grimoire_compiler)

    def get_architect_path(self):
        return os.path.join(settings.architects_dir, self.grimoire_architect)

    def get_formatter_path(self):
        return os.path.join(settings.formatter_dir, self.grimoire_formatter)
