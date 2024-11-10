from instant_prompt_box import InstantPromptBox

import zoltraak.llms.litellm_api as litellm
from zoltraak import settings
from zoltraak.schema.schema import MagicInfo
from zoltraak.utils.file_util import FileUtil
from zoltraak.utils.log_util import log, log_inout
from zoltraak.utils.subprocess_util import SubprocessUtil


class TargetCodeGenerator:
    def __init__(self, magic_info: MagicInfo):
        self.magic_info = magic_info
        self.file_info = magic_info.file_info
        self.first_code = ""
        self.last_code = ""
        self.last_exception = None

    def process_generated_code(self, code) -> str:
        """
        生成されたコードの処理を行うメソッド
        """
        self.append_source_hash_to_target_file()  # - ソースファイルのハッシュ値をターゲットファイルに追記

        if self.file_info.target_file_path.endswith(".py"):  # ターゲットファイルがPythonファイルの場合
            self.try_execute_generated_code(code)  # - 生成されたコードを実行
            return self.file_info.target_file_path
        # ターゲットファイルがpy以外の場合
        return self.file_info.target_file_path

    def write_code_to_target_file(self, target_file_path: str) -> None:
        """
        生成されたコードをターゲットファイルに書き込むメソッド
        """
        FileUtil.write_file(file_path=target_file_path, content=self.last_code)
        log(f"ターゲットファイルにコードを書き込みました: {target_file_path}")
        self.append_source_hash_to_target_file()  # - ソースファイルのハッシュ値をターゲットファイルに追記

    def append_source_hash_to_target_file(self):
        """
        ソースファイルのハッシュ値をターゲットファイルに追記するメソッド
        """
        # 過去のハッシュ値を削除
        with open(self.file_info.target_file_path, "r+", encoding="utf-8") as target_file:
            lines = target_file.readlines()
            if lines and lines[-1].startswith("# HASH:"):
                lines = lines[:-1]  # 最後の行がハッシュ値の場合、削除
                if lines and lines[-1] == "\n":  # 削除後に空白行が残っている場合、空白行も削除
                    lines = lines[:-1]
            target_file.seek(0)
            target_file.truncate()
            target_file.writelines(lines)

        log(f"source_hash: {self.file_info.source_hash}")
        if self.file_info.source_hash:  # ソースファイルのハッシュ値が指定されている場合
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
