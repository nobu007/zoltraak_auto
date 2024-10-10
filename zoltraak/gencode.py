import os
import shutil

import zoltraak.llms.litellm_api as litellm
from zoltraak import settings
from zoltraak.schema.schema import MagicInfo
from zoltraak.utils.file_util import FileUtil
from zoltraak.utils.log_util import log, log_inout
from zoltraak.utils.prompt_import import load_prompt
from zoltraak.utils.subprocess_util import SubprocessUtil


class TargetCodeGenerator:
    def __init__(self, magic_info: MagicInfo):
        self.magic_info = magic_info
        self.file_info = magic_info.file_info

    @log_inout
    def generate_target_code(self) -> str:
        """
        ソースファイルからターゲットファイルを生成するメソッド
        """
        # 1. 準備
        create_domain_grimoire, target_dir = self.prepare_generation()

        # 2. ソースファイルの読み込みと変数の作成
        source_content, source_file_name, variables = self.load_source_and_create_variables()

        # 3. プロンプトの読み込みとコード生成
        self.magic_info.prompt_final, code = self.load_prompt_and_generate_code(create_domain_grimoire, variables)

        # 4. 生成されたコードの処理
        self.process_generated_code(code)

        # 5. 結果の出力
        self.output_results()

        return self.file_info.target_file_path

    @log_inout
    def prepare_generation(self):
        """
        ターゲットコード生成の準備を行うメソッド
        """
        # target_file_pathからdevと.mdを省いて、generated/ の下につなげたものをtarget_dirに設定
        self.file_info.py_target_dir = (
            f"generated/{os.path.splitext(os.path.basename(self.file_info.target_file_path))[0]}"
        )

        self.print_step2_info(self.magic_info.grimoire_architect, self.file_info.py_target_dir)  # ステップ2の情報を出力

        if not self.file_info.past_source_file_path:  # 過去のソースファイルパスが指定されている場合
            self.save_current_source_as_past()  # - 現在のソースファイルを過去のソースファイルとして保存

        return self.magic_info.grimoire_architect, self.file_info.py_target_dir

    def print_step2_info(self, create_domain_grimoire, target_dir):
        """
        ステップ2の情報を出力するメソッド
        """
        log(
            f"""

==============================================================
ステップ2. 魔法術式を用いて領域術式を実行する
\033[32m領域術式\033[0m                      : {create_domain_grimoire}
\033[32m実行術式\033[0m                      : {self.file_info.target_file_path}
\033[32m領域対象\033[0m (ディレクトリパス)    : {target_dir}
==============================================================
        """
        )

    def load_source_and_create_variables(self):
        """
        ソースファイルの読み込みと変数の作成を行うメソッド
        """
        source_content = self.read_source_file()  # ソースファイルの内容を読み込む
        source_file_name = self.get_source_file_name()  # ソースファイルのファイル名（拡張子なし）を取得
        variables = self.create_variables_dict(source_content, source_file_name)  # 変数の辞書を作成

        return source_content, source_file_name, variables

    def load_prompt_and_generate_code(self, create_domain_grimoire, variables):
        """
        プロンプトの読み込みとコード生成を行うメソッド
        """
        prompt = self.load_prompt_with_variables(
            create_domain_grimoire, variables
        )  # 領域術式（要件定義書）からプロンプトを読み込み、変数を埋め込む
        code = self.generate_code(prompt)  # Claudeを使用してコードを生成

        return prompt, code

    def process_generated_code(self, code) -> str:
        """
        生成されたコードの処理を行うメソッド
        """
        self.write_code_to_target_file(code)  # 生成されたコードをターゲットファイルに書き込む

        log(f"source_hash: {self.file_info.source_hash}")
        if self.file_info.source_hash is not None:  # ソースファイルのハッシュ値が指定されている場合
            self.append_source_hash_to_target_file()  # - ソースファイルのハッシュ値をターゲットファイルに追記

        if self.file_info.target_file_path.endswith(".py"):  # ターゲットファイルがPythonファイルの場合
            self.try_execute_generated_code(code)  # - 生成されたコードを実行
            return self.file_info.target_file_path
        # ターゲットファイルがマークダウンファイルの場合
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
        """
        Claudeを使用してコードを生成するメソッド
        """
        # print("geminiを使用してコードを生成します")
        # code = gemini.generate_response(
        #     "gemini-1.5-pro"
        #     , prompt, 8192, 1
        # )
        code = litellm.generate_response(
            # "claude-3-haiku-20240307"
            # "claude-3-opus-20240229"
            settings.model_name,
            prompt,
            4000,
            0.3,
        )
        return code.replace("```python", "").replace("```", "")

    def write_code_to_target_file(self, code):
        """
        生成されたコードをターゲットファイルに書き込むメソッド
        """
        os.makedirs(os.path.dirname(self.file_info.target_file_path), exist_ok=True)
        with open(self.file_info.target_file_path, "w", encoding="utf-8") as target_file:
            target_file.write(code)
        log(f"ターゲットファイルにコードを書き込みました: {self.file_info.target_file_path}")

    def append_source_hash_to_target_file(self):
        """
        ソースファイルのハッシュ値をターゲットファイルに追記するメソッド
        """
        with open(self.file_info.target_file_path, "a", encoding="utf-8") as target_file:
            target_file.write(f"\n# HASH: {self.file_info.source_hash}\n")
        log(f"ターゲットファイルにハッシュ値を埋め込みました: {self.file_info.source_hash}")

    @log_inout
    def try_execute_generated_code(self, code):
        """
        生成されたコードを実行するメソッド
        なぜ書き込んだファイルではなくコードで実行するのか？
        ⇒エラー時の再実行でファイル読み書きせず再実行するため

        コメント: 最終的に修正したファイルを再書き込みしている。
        """
        while True:
            try:
                exec(code)  # noqa: S102
                break
            except Exception as e:  # noqa: BLE001
                log("Pythonファイルの実行中にエラーが発生しました。")
                log(f"\033[91mエラーメッセージ: {e!s}\033[0m")
                log(f"エラーが発生したPythonファイルのパス: \033[33m{self.file_info.target_file_path}\033[0m")

                while True:
                    prompt = f"""
                    以下のPythonコードにエラーがあります。修正してください。
                    コード: {code}
                    エラーメッセージ: {e!s}
                    プログラムコードのみ記載してください。
                    """
                    code = litellm.generate_response(
                        model=settings.model_name, prompt=prompt, max_tokens=4000, temperature=0.3
                    )
                    code = code.replace("```python", "").replace("```", "")

                    log("修正したコードを再実行します。")
                    try:
                        exec(code)  # noqa: S102
                        log("修正したコードの再実行が成功しました。")
                        break
                    except Exception as e2:  # noqa: BLE001
                        log("修正後のコードでもエラーが発生しました。再度修正を試みます。")
                        log(f"\033[91m修正後のエラーメッセージ: {e2!s}\033[0m")
                        log(code)
                        e = e2

                with open(self.file_info.target_file_path, "w", encoding="utf-8") as target_file:
                    target_file.write(code)

            # except Exception as e:
            #     print(f"Pythonファイルの実行中にエラーが発生しました。")
            #     print(f"\033[91mエラーメッセージ: {str(e)}\033[0m")
            #     print(f"エラーが発生したPythonファイルのパス: \033[33m{self.target_file_path}\033[0m")

            #     prompt = f"""
            #     Pythonファイルの実行中に以下のエラーが発生しました。
            #     ファイルの内容: {code}
            #     エラーメッセージ: {str(e)}
            #     考えられるエラーの原因と解決方法を教えてください。
            #     """
            #     response = generate_response(
            #         model="claude-3-haiku-20240307",
            #         prompt=prompt,
            #         max_tokens=1000,
            #         temperature=0.7
            #     )
            #     print(f"\033[33m{response}\033[0m")
            #     print("")

            #     user_input = input("コードを再実行しますか？ (y/n): ")
            #     if user_input.lower() != 'y':
            #         break
            #     else:
            #         prompt = f"""
            #         以下のPythonコードにエラーがあります。修正してください。
            #         コード: {code}
            #         エラーメッセージ: {str(e)}
            #         プログラムコードのみ記載してください。
            #         """
            #         code = generate_response(
            #             model="claude-3-haiku-20240307",
            #             prompt=prompt,
            #             max_tokens=4000,
            #             temperature=0.3
            #         )
            #         code = code.replace("```python", "").replace("```", "")

            #     print("次のコードを実行してください:")
            #     print(f"python {self.target_file_path}")
            #     import pyperclip
            #     pyperclip.copy(f"python {self.target_file_path}")
            #     print("コードをクリップボードにコピーしました。")

    def open_target_file_in_vscode(self):
        """
        ターゲットファイルをVS Codeで開くメソッド
        """
        SubprocessUtil.run(f"code {self.file_info.target_file_path}")

    def run_python_file(self):
        """
        Pythonファイルを実行するメソッド
        """
        print(f"Pythonファイルを実行します: {self.file_info.target_file_path}")
        SubprocessUtil.run(["python", self.file_info.target_file_path], check=False)
