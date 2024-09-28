
from pydantic import BaseModel, Field

from zoltraak import settings


class FileInfo(BaseModel):
    # 識別子
    canonical_name: str = Field(
        default="", description="対象のファイル群をシステム全体で一意に識別するための標準的な名前"
    )

    # Inputファイル
    md_file_path: str = Field(default="", description="処理対象のmdファイル")
    py_file_path: str = Field(default="", description="処理対象のpyファイル")

    # 処理対象ファイル
    source_file_path: str = Field(default="", description="ソースファイルパス")
    target_file_path: str = Field(default="", description="処理対象のファイルパス")
    past_source_file_path: str = Field(default="", description="過去のソースファイル")

    past_target_file_path: str = Field(default="", description="過去の出力先ファイル")
    past_source_folder: str = Field(default="past_md_files", description="過去のソースフォルダ")
    target_dir: str = Field(default="./output", description="出力先のディレクトリ")

    # その他
    source_hash: str = Field(default="", description="ソースファイルのハッシュ値")


class MagicInfo(BaseModel):
    # grimoire関連
    current_grimoire_name: str = Field(default="default_grimoire.md", description="現在のグリモアの名前")
    description: str = Field(default="汎用魔法式を展開します", description="現在のグリモアの説明")
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
    model_name: str = Field(default=settings.model_name, description="使用するLLMモデルの名前")
    prompt: str = Field(default="", description="使用するグリモアのプロンプト")
    success_message: str = Field(default="魔法式の構築が完了しました。", description="グリモア成功時のメッセージ")
    error_message: str = Field(
        default="魔法式の構築中にエラーが発生しました。", description="グリモア失敗時のメッセージ"
    )
    language: str = Field(default="", description="汎用言語指定(現状ではgrimoire_formatterに影響)")
