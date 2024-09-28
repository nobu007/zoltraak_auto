import os
from enum import Enum

from pydantic import BaseModel, Field

from zoltraak import settings


class MagicMode(Enum):
    GRIMOIRE_MODE = "grimoire_mode"  # プロンプト指定なしでグリモアのみ指定して実行
    PROMPT_MODE = "prompt_mode"  # グリモア＋プロンプト
    PROMPT_ONLY_MODE = "prompt_only_mode"  # プロンプト（グリモアなし）
    SEARCH_GRIMOIRE_MODE = "search_grimoire_mode"  # 最適なグリモアを検索


class FileInfo(BaseModel):
    # 識別子
    canonical_name: str = Field(
        default="zoltraak", description="対象のファイル群をシステム全体で一意に識別するための標準的な名前"
    )

    # Inputファイル
    md_file_path: str = Field(
        default="ARCHITECTURE.md",
        description="処理対象のmdファイル(カレントからの相対パス or grimoires_dirからの相対パス or 絶対パス)",
    )
    md_file_path_abs: str = Field(
        default=os.path.join(settings.zoltraak_dir, "ARCHITECTURE.md"),
        description="処理対象のmdファイル(絶対パス)",
    )
    py_file_path: str = Field(
        default="ARCHITECTURE.py", description="処理対象のpyファイル(カレントからの相対パス or 絶対パス)"
    )
    py_file_path_abs: str = Field(
        default=os.path.join(settings.zoltraak_dir, "ARCHITECTURE.py"), description="処理対象のpyファイル(絶対パス)"
    )

    # 処理対象ファイル
    source_file_path: str = Field(default="", description="ソースファイルパス(絶対パス)")
    target_file_path: str = Field(default="", description="処理対象のファイルパス(絶対パス)")
    past_source_file_path: str = Field(default="", description="過去のソースファイル")

    past_target_file_path: str = Field(default="", description="過去の出力先ファイル(絶対パス)")
    past_source_folder: str = Field(default="past_md_files", description="過去のソースフォルダ")
    target_dir: str = Field(default="./output", description="出力先のディレクトリ")

    # その他
    source_hash: str = Field(default="", description="ソースファイルのハッシュ値")

    def update(self):
        self.md_file_path_abs = os.path.abspath(self.md_file_path)
        self.py_file_path_abs = os.path.abspath(self.py_file_path)


class MagicInfo(BaseModel):
    # コア情報
    magic_mode: str = Field(default=MagicMode.GRIMOIRE_MODE, description="実行モード")
    model_name: str = Field(default=settings.model_name, description="使用するLLMモデルの名前")
    prompt: str = Field(
        default="zoltraakシステムのARCHITECTURE.mdを更新してください。", description="使用するグリモアのプロンプト"
    )

    # grimoire関連
    current_grimoire_name: str = Field(
        default="dev_obj.md", description="現在実行中のグリモア名(generate_xx関数の先頭で設定)"
    )
    description: str = Field(
        default="汎用魔法式を展開します", description="現在実行中の説明(generate_xx関数の先頭で設定)"
    )
    grimoire_compiler: str = Field(default="dev_obj.md", description="使用するグリモアコンパイラのファイル名")
    grimoire_architect: str = Field(
        default="architect_claude.md", description="使用するグリモアアーキテクトのファイル名"
    )
    grimoire_formatter: str = Field(
        default="md_comment.md", description="使用するグリモアフォーマッタのファイル名(=language)"
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
