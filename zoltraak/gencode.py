import os
import shutil

from instant_prompt_box import InstantPromptBox

import zoltraak.llms.litellm_api as litellm
from zoltraak import settings
from zoltraak.core.prompt_manager import PromptEnum
from zoltraak.schema.schema import MagicInfo
from zoltraak.utils.file_util import FileUtil
from zoltraak.utils.log_util import log, log_inout
from zoltraak.utils.prompt_import import load_prompt
from zoltraak.utils.subprocess_util import SubprocessUtil


class TargetCodeGenerator:
    def __init__(self, magic_info: MagicInfo):
        self.magic_info = magic_info
        self.file_info = magic_info.file_info
        self.first_code = ""
        self.last_code = ""
        self.last_exception = None

    # @log_inout
    # def generate_target_code(self) -> str:
    #     """
    #     ソースファイルからターゲットファイルを生成するメソッド
    #     """
    #     # 1. 準備
    #     create_domain_grimoire, target_dir = self.prepare_generation()

    #     # 2. ソースファイルの読み込みと変数の作成
    #     source_content, source_file_name, variables = self.load_source_and_create_variables()

    #     # 3. プロンプトの読み込みとコード生成
    #     self.magic_info.prompt_final, code = self.load_prompt_and_generate_code(create_domain_grimoire, variables)

    #     # 4. 生成されたコードの処理
    #     self.process_generated_code(code)

    #     # 5. 結果の出力
    #     self.output_results()

    #     return self.file_info.target_file_path

    # @log_inout
    #     def prepare_generation(self):
    #         """
    #         ターゲットコード生成の準備を行うメソッド
    #         """
    #         # target_file_pathからdevと.mdを省いて、generated/ の下につなげたものをtarget_dirに設定
    #         self.file_info.py_target_dir = (
    #             f"generated/{os.path.splitext(os.path.basename(self.file_info.target_file_path))[0]}"
    #         )

    #         self.print_step2_info(self.magic_info.grimoire_architect, self.file_info.py_target_dir)

    #         if not self.file_info.past_source_file_path:  # 過去のソースファイルパスが指定されている場合
    #             self.save_current_source_as_past()  # - 現在のソースファイルを過去のソースファイルとして保存

    #         return self.magic_info.grimoire_architect, self.file_info.py_target_dir

    #     def print_step2_info(self, create_domain_grimoire, target_dir):
    #         """
    #         ステップ2の情報を出力するメソッド
    #         """
    #         log(
    #             f"""

    # ==============================================================
    # ステップ2. 魔法術式を用いて領域術式を実行する
    # \033[32m領域術式\033[0m                      : {create_domain_grimoire}
    # \033[32m実行術式\033[0m                      : {self.file_info.target_file_path}
    # \033[32m領域対象\033[0m (ディレクトリパス)    : {target_dir}
    # ==============================================================
    #         """
    #         )

    # def load_source_and_create_variables(self):
    #     """
    #     ソースファイルの読み込みと変数の作成を行うメソッド
    #     """
    #     source_content = self.read_source_file()  # ソースファイルの内容を読み込む
    #     source_file_name = self.get_source_file_name()  # ソースファイルのファイル名（拡張子なし）を取得
    #     variables = self.create_variables_dict(source_content, source_file_name)  # 変数の辞書を作成

    #     return source_content, source_file_name, variables

    # def load_prompt_and_generate_code(self, create_domain_grimoire, variables):
    #     """
    #     プロンプトの読み込みとコード生成を行うメソッド
    #     """
    #     prompt = self.load_prompt_with_variables(
    #         create_domain_grimoire, variables
    #     )  # 領域術式（要件定義書）からプロンプトを読み込み、変数を埋め込む
    #     code = self.generate_code(prompt)

    #     return prompt, code

    def process_generated_code(self, code) -> str:
        """
        生成されたコードの処理を行うメソッド
        """
        log(f"source_hash: {self.file_info.source_hash}")
        if self.file_info.source_hash is not None:  # ソースファイルのハッシュ値が指定されている場合
            self.append_source_hash_to_target_file()  # - ソースファイルのハッシュ値をターゲットファイルに追記

        if self.file_info.target_file_path.endswith(".py"):  # ターゲットファイルがPythonファイルの場合
            self.try_execute_generated_code(code)  # - 生成されたコードを実行
            return self.file_info.target_file_path
        # ターゲットファイルがpy以外の場合
        return self.file_info.target_file_path

    def output_results(self):
        """
        結果の出力を行うメソッド
        """
        self.file_info.add_output_file_path(self.file_info.target_file_path)
        log("target_file_path: %s", self.file_info.target_file_path)

    def save_current_source_as_past(self):
        """
        現在のソースファイルを過去のソースファイルとして保存するメソッド
        """
        shutil.copy(self.file_info.source_file_path, self.file_info.past_source_file_path)

    def read_source_file(self):
        """
        ソースファイルの内容を読み込むメソッド
        """
        return FileUtil.read_file(self.file_info.source_file_path)

    def get_source_file_name(self):
        """
        ソースファイルのファイル名（拡張子なし）を取得するメソッド
        """
        source_file_name = os.path.splitext(os.path.basename(self.file_info.source_file_path))[0]
        if source_file_name.startswith("def_"):
            source_file_name = source_file_name[4:]
        return source_file_name

    def create_variables_dict(self, source_content, source_file_name):
        """
        変数の辞書を作成するメソッド
        """
        return {
            "source_file_path": self.file_info.source_file_path,
            "source_file_name": source_file_name,
            "source_content": source_content,
        }

    def load_prompt_with_variables(self, create_domain_grimoire, variables):
        """
        領域術式（要件定義書）からプロンプトを読み込み、変数を埋め込むメソッド
        """
        log("create_domain_grimoire=%s", create_domain_grimoire)
        return load_prompt(create_domain_grimoire, variables)

    def generate_code(self, prompt):
        code = self.generate_response(
            prompt_enum=PromptEnum.FINAL,
            prompt=prompt,
            max_tokens=settings.max_tokens_generate_code,
            temperature=settings.temperature_generate_code,
        )
        return code.replace("```python", "").replace("```", "")

    # def write_code_to_target_file(self, code):
    #     """
    #     生成されたコードをターゲットファイルに書き込むメソッド
    #     """
    #     os.makedirs(os.path.dirname(self.file_info.target_file_path), exist_ok=True)
    #     with open(self.file_info.target_file_path, "w", encoding="utf-8") as target_file:
    #         target_file.write(code)
    #     log(f"ターゲットファイルにコードを書き込みました: {self.file_info.target_file_path}")

    def append_source_hash_to_target_file(self):
        """
        ソースファイルのハッシュ値をターゲットファイルに追記するメソッド
        """
        with open(self.file_info.target_file_path, "a", encoding="utf-8") as target_file:
            target_file.write(f"\n# HASH: {self.file_info.source_hash}\n")
        log(f"ターゲットファイルにハッシュ値を埋め込みました: {self.file_info.source_hash}")

    @log_inout
    def try_execute_generated_code_one(self, code) -> bool:
        """生成されたコードを実行するメソッド(汎用)

        Args:
            code (_type_): _description_
        """
        try:
            self.last_code = code
            exec(code)  # noqa: S102
            log("コードの実行が成功しました。")
        except Exception as e:  # noqa: BLE001
            log("コードでエラーが発生しました。修正を試みます。")
            log(f"\033[91mエラーメッセージ: {e!s}\033[0m")
            self.last_exception = e
            return False
        self.last_exception = None
        return True

    @log_inout
    def try_execute_generated_code(self, code) -> bool:
        """
        生成されたコードを実行するメソッド
        なぜ書き込んだファイルではなくコードで実行するのか？
        ⇒エラー時の再実行でファイル読み書きせず再実行するため

        コメント: 最終的に修正したファイルを再書き込みしている。
        """
        max_try_count = 3
        for i in range(max_try_count):
            if self.try_execute_generated_code_one(code):
                log(f"コード実行に成功しました。try{i}")
                return True

            fix_code_prompt = InstantPromptBox.zoltraak.zoltraak_prompt_fix_code(
                code=code, error_message=str(self.last_exception)
            )
            code = self.get_fixed_code(code, fix_code_prompt)
            log(f"修正したコードを再実行します。try{i}")
        log(f"{max_try_count}回トライしましたが、エラーが解消できませんでした。スマート推論を試みます。")
        return self.try_execute_generated_code_smart(code)

    @log_inout
    def try_execute_generated_code_smart(self, code) -> bool:
        """エラー解消が難航したときに、エラーの原因を特定して修正するメソッド
        TODO: smartなllmを使う＆プロンプト最適化
        """
        max_try_count = 3
        for i in range(max_try_count):
            error_reason = self.get_error_reason(code)
            fix_code_prompt = InstantPromptBox.zoltraak.zoltraak_prompt_fix_code_smart(
                code=code, error_message=str(self.last_exception), error_reason=error_reason
            )
            code = self.get_fixed_code(code, fix_code_prompt)
            log(f"修正したコードを再実行します(スマート推論)。retry{i}")

            if self.try_execute_generated_code_one(code):
                log(f"コード実行に成功しました(スマート推論)。try{i}")
                return True

        log(
            f"{max_try_count}回のスマート推論でもエラーが解消できませんでした。コードを確認してください。 %s",
            self.file_info.target_file_path,
        )
        return False

    @log_inout
    def get_fixed_code(self, code: str, fix_code_prompt: str) -> str:
        """コードエラーを解消する処理"""
        code = litellm.generate_response(
            model=settings.model_name,
            prompt=fix_code_prompt,
            max_tokens=settings.max_tokens_generate_code_fix,
            temperature=settings.temperature_generate_code_fix,
        )
        code = code.replace("```python", "").replace("```", "")
        log("コードを修正しました。len(code)=%s", len(code))
        return code

    @log_inout
    def get_error_reason(self, code):
        """エラー解消が難航したときに、エラーの原因を推定する"""
        error_reason_prompt = f"""
        以下のPythonコードにエラーがあります。
        コード: {code}
        エラーメッセージ: {self.last_exception!s}
        考えられるエラーの原因と解決方法を教えてください。
        推論が発散しないように、簡潔な説明をお願いします。
        プログラムコードを回答する場合は関数単位やブロック単位で完全なコードを記載してください。
        """
        error_reason = litellm.generate_response(
            model=settings.model_name,
            prompt=error_reason_prompt,
            max_tokens=settings.max_tokens_generate_error_reason,
            temperature=settings.temperature_generate_error_reason,
        )
        log("error_reason=%s", error_reason)
        return error_reason

    def open_target_file_in_vscode(self):
        """
        ターゲットファイルをVS Codeで開くメソッド
        """
        SubprocessUtil.run(f"code {self.file_info.target_file_path}")

    def run_python_file(self):
        """
        Pythonファイルを実行するメソッド
        """
        log(f"Pythonファイルを実行します: {self.file_info.target_file_path}")
        SubprocessUtil.run(["python", self.file_info.target_file_path], check=False)
