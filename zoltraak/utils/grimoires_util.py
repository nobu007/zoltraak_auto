import os

from zoltraak import settings
from zoltraak.utils.log_util import log


class GrimoireUtil:
    @staticmethod
    def prepare_compiler(input_: str, compiler: str, custom_compiler: str) -> str:
        # compilerが有効かチェック
        valid_compiler = GrimoireUtil.get_valid_compiler(compiler)
        if valid_compiler:
            return valid_compiler

        # custom_compilerが有効かチェック
        valid_compiler = GrimoireUtil.get_valid_compiler(custom_compiler)
        if valid_compiler:
            return valid_compiler

        # inputで指定されたcompilerが有効かチェック
        valid_compiler = GrimoireUtil.get_valid_compiler(input_)
        if valid_compiler:
            return valid_compiler

        # inputでcompilerが指定されているかチェック
        valid_compiler = GrimoireUtil.get_valid_compiler(compiler)
        if valid_compiler:
            return valid_compiler

        # どれも無効な場合はデフォルトコンパイラを返す
        return GrimoireUtil.get_valid_compiler("dev_obj")

    @staticmethod
    def get_valid_compiler(compiler_candidate: str) -> str:
        """有効なcompilerだったらその絶対パスを返す
        無効なら空文字を返す"""
        return GrimoireUtil.get_valid_markdown(compiler_candidate, settings.compiler_dir)

    @staticmethod
    def get_valid_architect(compiler_candidate: str) -> str:
        """有効なarchitectだったらその絶対パスを返す
        無効なら空文字を返す"""
        return GrimoireUtil.get_valid_markdown(compiler_candidate, settings.architects_dir)

    @staticmethod
    def get_valid_formatter(compiler_candidate: str) -> str:
        """有効なformatterだったらその絶対パスを返す
        無効なら空文字を返す"""
        return GrimoireUtil.get_valid_markdown(compiler_candidate, settings.formatter_dir)

    @staticmethod
    def get_valid_markdown(markdown_candidate: str, additional_dir: str = "") -> str:
        """有効だったらその絶対パスを返す
        無効なら空文字を返す"""
        if not markdown_candidate:
            log("空文字")
            return ""

        # 拡張子".md"を準備して、以降はファイル存在チェックする
        if not markdown_candidate.endswith(".md"):
            markdown_candidate += ".md"

        # カレントディレクトリをチェック(絶対パスで来た場合もここで返す)
        candidate_abs = os.path.abspath(markdown_candidate)
        if os.path.isfile(candidate_abs):
            log("検出 " + candidate_abs)
            return candidate_abs

        # additional_dir配下をチェック
        if additional_dir:
            candidate_abs = os.path.join(additional_dir, markdown_candidate)
            if os.path.isfile(candidate_abs):
                log("検出(additional_dir配下) " + candidate_abs)
                return candidate_abs

        log("無効 " + markdown_candidate)
        return ""
