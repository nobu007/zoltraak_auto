import hashlib
import os

import zoltraak.llms.litellm_api as litellm
from zoltraak import settings
from zoltraak.gencode import TargetCodeGenerator
from zoltraak.md_generator import generate_md_from_prompt
from zoltraak.utils.rich_console import MagicInfo, display_magic_info_full
from zoltraak.utils.subprocess_util import SubprocessUtil


class MarkdownToPythonConverter:
    def __init__(self, magic_info: MagicInfo):
        self.magic_info = magic_info

    def convert(self):
        file_info = self.magic_info.file_info
        if self.magic_info.prompt is None:  # プロンプトが指定されていない場合
            file_info.source_file_path = file_info.md_file_path  # - ソースファイルパスをマークダウンファイルパスに設定
            file_info.target_file_path = file_info.py_file_path  # - ターゲットファイルパスをPythonファイルパスに設定
            file_info.past_source_folder = "past_md_files"  # - 過去のソースフォルダを "past_md_files" に設定
        else:  # プロンプトが指定されている場合
            file_info.source_file_path = file_info.md_file_path  # - ソースファイルパスをマークダウンファイルパスに設定
            file_info.target_file_path = (
                file_info.md_file_path
            )  # - ターゲットファイルパスをマークダウンファイルパスに設定
            file_info.past_source_folder = "past_prompt_files"  # - 過去のソースフォルダを "past_prompt_files" に設定

            if os.path.exists(file_info.md_file_path):  # -- マークダウンファイルが存在する場合
                display_magic_info_full(self.magic_info)
                print(
                    f"{file_info.md_file_path}は既存のファイルです。promptに従って変更を提案します。"
                )  # --- ファイルが既存であることを示すメッセージを表示
                self.propose_target_diff(
                    file_info.target_file_path, self.magic_info.prompt
                )  # --- プロンプトに従ってターゲットファイルの差分を提案
                return ""  # --- 関数を終了

        if os.path.exists(file_info.source_file_path):  # ソースファイルが存在する場合
            file_info.source_hash = self.calculate_file_hash(
                file_info.source_file_path
            )  # - ソースファイルのハッシュ値を計算
        os.makedirs(file_info.past_source_folder, exist_ok=True)  # - 過去のソースフォルダを作成（既存の場合はスキップ）
        file_info.past_source_file_path = os.path.join(
            file_info.past_source_folder, os.path.basename(file_info.source_file_path)
        )  # - 過去のソースファイルパスを設定

        if os.path.exists(file_info.target_file_path):  # ターゲットファイルが存在する場合
            self.handle_existing_target_file()  # - 既存のターゲットファイルを処理
            return None
        # ターゲットファイルが存在しない場合
        self.handle_new_target_file()  # - 新しいターゲットファイルを処理
        return None

    def calculate_file_hash(self, file_path):
        with open(file_path, "rb") as file:
            content = file.read()
            return hashlib.sha256(content).hexdigest()

    def handle_existing_target_file(self) -> str:
        file_info = self.magic_info.file_info
        with open(file_info.target_file_path, encoding="utf-8") as target_file:
            lines = target_file.readlines()
            if len(lines) > 0 and lines[-1].startswith("# HASH: "):
                embedded_hash = lines[-1].split("# HASH: ")[1].strip()
                if file_info.source_hash == embedded_hash:
                    if self.magic_info.prompt is None:
                        SubprocessUtil.run(["python", file_info.target_file_path], check=False)
                    else:
                        with open(file_info.target_file_path, encoding="utf-8") as md_file:
                            return md_file.read()
                else:
                    print(f"{file_info.source_file_path}の変更を検知しました。")
                    print("ソースファイルの差分:")
                    if os.path.exists(file_info.past_source_file_path):
                        self.display_source_diff()
        return ""

    def display_source_diff(self):
        file_info = self.magic_info.file_info
        import difflib

        with open(file_info.past_source_file_path, encoding="utf-8") as old_source_file:
            old_source_lines = old_source_file.readlines()
        with open(file_info.source_file_path, encoding="utf-8") as new_source_file:
            new_source_lines = new_source_file.readlines()

        source_diff = difflib.unified_diff(old_source_lines, new_source_lines, lineterm="", n=0)
        source_diff_text = "".join(source_diff)
        print(source_diff_text)

        self.propose_target_diff(file_info.target_file_path, self.magic_info.prompt)
        print(f"ターゲットファイル: {file_info.target_file_path}")
        # input("修正が完了したらEnterキーを押してください。")

    def handle_new_target_file(self) -> str:
        file_info = self.magic_info.file_info
        if self.magic_info.prompt is None:
            print(
                f"""
高級言語コンパイル中: {file_info.target_file_path}は新しいファイルです。少々お時間をいただきます。
{file_info.source_file_path} -> {file_info.target_file_path}
                  """
            )
            target = TargetCodeGenerator(self.magic_info)
            return target.generate_target_code()
        print(
            f"""
    {"検索結果生成中" if self.magic_info.current_grimoire_name is None else "要件定義書執筆中"}:
    {file_info.target_file_path}は新しいファイルです。少々お時間をいただきます。
    {file_info.source_file_path} -> {file_info.target_file_path}
            """
        )
        return generate_md_from_prompt(self.magic_info)

    def propose_target_diff(self, target_file_path, prompt=None):
        """
        ターゲットファイルの変更差分を提案する関数

        Args:
            target_file_path (str): 現在のターゲットファイルのパス
            prompt (str): promptの内容
        """
        # プロンプトにターゲットファイルの内容を変数として追加
        with open(target_file_path, encoding="utf-8") as target_file:
            current_target_code = target_file.read()
        prompt_additional_part = ""
        if prompt:
            prompt_additional_part = f"""
promptの内容:
{prompt}
をもとに、
"""
        prompt = f"""
現在のターゲットファイルの内容:
{current_target_code}

上記から
{prompt_additional_part}

ターゲットファイルの変更が必要な部分"のみ"をプログラムで出力してください。
出力はunified diff形式で、削除した文を薄い赤色、追加した文を薄い緑色にして

@@ -1,4 +1,4 @@
 line1
-line2
+line2 modified
 line3
-line4
+line4 modified

        """
        response = litellm.generate_response(
            model=settings.model_name_lite,
            prompt=prompt,
            max_tokens=1000,
            temperature=0.0,
        )
        target_diff = response.strip()
        # ターゲットファイルの差分を表示
        print("ターゲットファイルの差分:")
        print(target_diff)

        # ユーザーに適用方法を尋ねる
        print("差分をどのように適用しますか？")
        print("1. AIで適用する")
        # print("2. 自分で行う")
        # print("3. 何もせず閉じる")
        # choice = input("選択してください (1, 2, 3): ")
        choice = "1"

        while True:
            if choice == "1":
                # 差分をターゲットファイルに自動で適用
                self.apply_diff_to_target_file(target_file_path, target_diff)
                print(f"{target_file_path}に差分を自動で適用しました。")
                break
            if choice == "2":
                print("手動で差分を適用してください。")
                break
            if choice == "3":
                print("操作をキャンセルしました。")
                break
            print("無効な選択です。もう一度選択してください。")
            print("1. 自動で適用する")
            # print("2. エディタで行う")
            # print("3. 何もせず閉じる")
            # choice = input("選択してください (1, 2, 3): ")
            choice = "1"

    def apply_diff_to_target_file(self, target_file_path, target_diff):
        """
        提案された差分をターゲットファイルに適用する関数

        Args:
            target_file_path (str): ターゲットファイルのパス
            target_diff (str): 適用する差分
        """
        # ターゲットファイルの現在の内容を読み込む
        with open(target_file_path, encoding="utf-8") as file:
            current_content = file.read()

        # プロンプトを作成してAPIに送信し、修正された内容を取得
        prompt = f"""
現在のターゲットファイルの内容:
{current_content}
上記のターゲットファイルの内容に対して、以下のUnified diff 適用後のターゲットファイルの内容を生成してください。

提案された差分:
{target_diff}

例）
変更前
- graph.node(week_node_name, shape='box', style='filled', fillcolor='#FFCCCC')

変更後
+ graph.node(week_node_name, shape='box', style='filled', fillcolor='#CCCCFF')

番号など変わった場合は振り直しもお願いします。
        """
        modified_content = litellm.generate_response(settings.model_name, prompt, 2000, 0.3)

        # 修正後の内容をターゲットファイルに書き込む
        with open(target_file_path, "w", encoding="utf-8") as file:
            file.write(modified_content)

        print(f"{target_file_path}に修正を適用しました。")
