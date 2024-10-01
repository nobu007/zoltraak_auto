import os

import zoltraak.llms.litellm_api as litellm
from zoltraak import settings
from zoltraak.gen_markdown import generate_md_from_prompt
from zoltraak.schema.schema import MagicInfo, MagicMode
from zoltraak.utils.file_util import FileUtil
from zoltraak.utils.log_util import log, log_inout
from zoltraak.utils.rich_console import display_magic_info_full


class BaseConverter:
    """コンバーターの共通処理はこちら
    前提:
      MagicInfoにモードとレイヤーが展開済み
        MagicMode
        MagicLayer
      MagicInfo.FileInfoに入出力ファイルが展開済み
        prompt_file_path
        pre_md_file_path
        md_file_path
        py_file_path
    """

    def __init__(self, magic_info: MagicInfo):
        self.magic_info = magic_info

    def convert(self) -> str:
        """生成処理"""
        return self.convert_one()

    @log_inout
    def convert_one(self) -> str:
        """生成処理を１回実行する"""
        file_info = self.magic_info.file_info
        self.update_grimoire_and_prompt()

        # ソースファイルの有無による分岐
        if os.path.exists(file_info.source_file_path):  # -- マークダウンファイルが存在する場合
            log(f"既存のソースファイル {file_info.source_file_path} が存在しました。")
            self.magic_info.prompt += "\n\n<<追加指示>>\n"
            self.magic_info.prompt += FileUtil.read_file(file_info.source_file_path)
        else:
            # 次回に備えてソースファイルを保存
            FileUtil.write_file(file_info.source_file_path, self.magic_info.prompt)

        # ソースファイルまでプロンプトに反映できた時点でデバッグ表示
        display_magic_info_full(self.magic_info)

        # ターゲットファイルの有無による分岐
        if os.path.exists(file_info.target_file_path):  # ターゲットファイルが存在する場合
            return self.handle_existing_target_file()  # - 既存のターゲットファイルを処理
        # ターゲットファイルが存在しない場合
        return self.handle_new_target_file()  # - 新しいターゲットファイルを処理

    @log_inout
    def update_grimoire_and_prompt(self):
        # モードによる分岐
        log(f"{self.magic_info.magic_mode}で変更を提案します。")
        if self.magic_info.magic_mode is MagicMode.GRIMOIRE_ONLY:
            # グリモアのみ
            if not os.path.isfile(self.magic_info.get_compiler_path()):
                log("コンパイラが存在しないため、一般的なプロンプトを使用します。")
                self.magic_info.grimoire_compiler = "general_prompt.md"
            self.magic_info.prompt = ""
        elif self.magic_info.magic_mode is MagicMode.GRIMOIRE_AND_PROMPT:
            # グリモアまたはプロンプトどちらか TODO: 用語をコンパイラに統一したい
            if not os.path.isfile(self.magic_info.get_compiler_path()):
                self.magic_info.grimoire_compiler = ""
                if not self.magic_info.prompt:
                    log("コンパイラもプロンプトも未設定のため、一般的なプロンプトを使用します。")
                    self.magic_info.prompt = FileUtil.read_grimoire("general_prompt.md")
        elif self.magic_info.magic_mode is MagicMode.PROMPT_ONLY:
            # プロンプトのみ
            self.magic_info.grimoire_compiler = ""
            if not self.magic_info.prompt:
                log("プロンプトが未設定のため、一般的なプロンプトを使用します。")
                self.magic_info.prompt = FileUtil.read_grimoire("general_prompt.md")
        else:
            # SEARCH_GRIMOIRE(ノーケア、別のところで処理すること！)
            log("(SEARCH_GRIMOIRE)一般的なプロンプトを使用します。")
            if not os.path.isfile(self.magic_info.get_compiler_path()):
                self.magic_info.grimoire_compiler = ""
                self.magic_info.prompt = FileUtil.read_grimoire("general_prompt.md")

    @log_inout
    def handle_existing_target_file(self) -> str:
        file_info = self.magic_info.file_info
        is_source_changed = True  # TODO: hash check
        if is_source_changed:
            print(f"{file_info.source_file_path}の変更を検知しました。")
            if os.path.exists(file_info.past_source_file_path):
                return self.update_target_file_from_source_diff()
            return self.update_target_file_propose_and_apply(file_info.target_file_path, self.magic_info.prompt)
        # ソースファイルが変わってない場合は再処理する
        return self.update_target_file_propose_and_apply(file_info.target_file_path, self.magic_info.prompt)

    @log_inout
    def update_target_file_from_source_diff(self) -> str:
        file_info = self.magic_info.file_info
        import difflib

        with open(file_info.past_source_file_path, encoding="utf-8") as old_source_file:
            old_source_lines = old_source_file.readlines()
        with open(file_info.source_file_path, encoding="utf-8") as new_source_file:
            new_source_lines = new_source_file.readlines()

        source_diff = difflib.unified_diff(old_source_lines, new_source_lines, lineterm="", n=0)
        source_diff_text = "".join(source_diff)
        log(f"source_diff_text={source_diff_text}")

        self.magic_info.prompt += "\n\n<<(注意)重要な変化点(注意)>>\n"
        self.magic_info.prompt += source_diff_text

        return self.update_target_file_propose_and_apply(file_info.target_file_path, self.magic_info.prompt)

    def update_target_file_propose_and_apply(self, target_file_path, prompt=None) -> str:
        """
        ターゲットファイルの変更差分を提案して適用する関数

        Args:
            target_file_path (str): 現在のターゲットファイルのパス
            prompt (str): promptの内容
        """
        # プロンプトにターゲットファイルの内容を変数として追加
        current_target_code = FileUtil.read_file(target_file_path)
        prompt_additional_part = ""
        if prompt:
            prompt_additional_part = f"""
promptの内容:
{prompt}
をもとに、
"""
        final_prompt = f"""
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
            prompt=final_prompt,
            max_tokens=1000,
            temperature=0.0,
        )
        target_diff = response.strip()
        # ターゲットファイルの差分を表示
        log("ターゲットファイルの差分:")
        log(target_diff)

        # ユーザーに適用方法を尋ねる
        print("差分をどのように適用しますか?")
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

        return target_file_path

    @log_inout
    def apply_diff_to_target_file(self, target_file_path, target_diff) -> str:
        """
        提案された差分をターゲットファイルに適用する関数

        Args:
            target_file_path (str): ターゲットファイルのパス
            target_diff (str): 適用する差分
        """
        # ターゲットファイルの現在の内容を読み込む
        current_content = FileUtil.read_file(target_file_path)

        # プロンプトを作成してAPIに送信し、修正された内容を取得
        prompt = f"""
現在のターゲットファイルの内容:
{current_content}
上記のターゲットファイルの内容に対して、以下のUnified diff 適用後のターゲットファイルの内容を生成してください。

提案された差分:
{target_diff}

例)
変更前
- graph.node(week_node_name, shape='box', style='filled', fillcolor='#FFCCCC')

変更後
+ graph.node(week_node_name, shape='box', style='filled', fillcolor='#CCCCFF')

番号など変わった場合は振り直しもお願いします。
        """
        modified_content = litellm.generate_response(settings.model_name, prompt, 2000, 0.3)

        # 修正後の内容をターゲットファイルに書き込む
        new_target_file_path = FileUtil.write_file(target_file_path, modified_content)

        print(f"{new_target_file_path}に修正を適用しました。")
        return new_target_file_path

    @log_inout
    def handle_new_target_file(self):
        file_info = self.magic_info.file_info
        print(f"""
{file_info.target_file_path}は新しいファイルです。少々お時間をいただきます。
{file_info.source_file_path} -> {file_info.target_file_path}
                  """)

        return generate_md_from_prompt(self.magic_info)


if __name__ == "__main__":  # このスクリプトが直接実行された場合にのみ、以下のコードを実行します。
    magic_info_ = MagicInfo()
    converter = BaseConverter(magic_info_)
    converter.convert()
