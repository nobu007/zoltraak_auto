import os

import zoltraak.llms.litellm_api as litellm
from zoltraak import settings
from zoltraak.core.magic_workflow import MagicWorkflow
from zoltraak.gen_markdown import generate_md_from_prompt
from zoltraak.schema.schema import MagicLayer, MagicMode
from zoltraak.utils.file_util import FileUtil
from zoltraak.utils.grimoires_util import GrimoireUtil
from zoltraak.utils.log_util import log, log_e, log_inout


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

    def __init__(self, magic_workflow: MagicWorkflow):
        self.magic_workflow = magic_workflow
        self.magic_info = magic_workflow.magic_info

    def convert_loop(self) -> str:
        """ダミー"""
        acceptable_layers = [MagicLayer.LAYER_1_REQUEST_GEN]
        return self.magic_workflow.run_loop(self.convert, acceptable_layers)

    def convert(self) -> str:
        """生成処理"""
        final_output_file_path = self.magic_workflow.run(self.convert_one)
        self.magic_info.file_info.final_output_file_path = final_output_file_path
        return final_output_file_path

    @log_inout
    def convert_one(self) -> str:
        """生成処理を１回実行する"""
        file_info = self.magic_info.file_info
        self.update_grimoire_and_prompt()

        # ソースファイルの有無による分岐
        if FileUtil.has_content(file_info.source_file_path):  # -- マークダウンファイルが存在する場合
            log(f"既存のソースファイル {file_info.source_file_path} が存在しました。")
            self.magic_info.prompt += "\n\n<<追加指示>>\n"
            self.magic_info.prompt += FileUtil.read_file(file_info.source_file_path)
        else:
            # ソースファイルを保存(設計では初回のprompt_file_pathにだけ保存する)
            FileUtil.write_file(file_info.source_file_path, self.magic_info.prompt)

        # ターゲットファイルの有無による分岐
        if FileUtil.has_content(file_info.target_file_path):  # ターゲットファイルが存在する場合
            return self.handle_existing_target_file()  # - 既存のターゲットファイルを処理
        # ターゲットファイルが存在しない場合
        return self.handle_new_target_file()  # - 新しいターゲットファイルを処理

    @log_inout
    def update_grimoire_and_prompt(self):
        # モードによる分岐
        log(f"{self.magic_info.magic_mode}で変更を提案します。")

        # コンパイラのパスを取得
        compiler_path = GrimoireUtil.get_valid_compiler(self.magic_info.grimoire_compiler)
        default_compiler_path = GrimoireUtil.get_valid_compiler("general_prompt.md")

        if self.magic_info.magic_mode is MagicMode.GRIMOIRE_ONLY:
            # グリモアのみ
            if not os.path.isfile(compiler_path):
                log("コンパイラが存在しないため、デフォルトのコンパイラを使用します。")
                compiler_path = default_compiler_path
            self.magic_info.prompt = ""
        elif self.magic_info.magic_mode is MagicMode.GRIMOIRE_AND_PROMPT:
            # グリモアまたはプロンプトどちらか TODO: 用語をコンパイラに統一したい
            if not os.path.isfile(compiler_path):
                compiler_path = ""
                if not self.magic_info.prompt:
                    log("コンパイラもプロンプトも未設定のため、一般的なプロンプトを使用します。")
                    compiler_path = ""
                    self.magic_info.prompt = FileUtil.read_grimoire(default_compiler_path)
        elif self.magic_info.magic_mode is MagicMode.PROMPT_ONLY:
            # プロンプトのみ
            compiler_path = ""
            if not self.magic_info.prompt:
                log("プロンプトが未設定のため、一般的なプロンプトを使用します。")
                self.magic_info.prompt = FileUtil.read_grimoire(default_compiler_path)
        else:
            # SEARCH_GRIMOIRE or ZOLTRAAK_LEGACY(ノーケア、別のところで処理すること！)
            log("(SEARCH_GRIMOIRE)一般的なプロンプトを使用します。")
            if not os.path.isfile(compiler_path):
                compiler_path = default_compiler_path
                self.magic_info.prompt = FileUtil.read_grimoire(default_compiler_path)

        # レイヤによる分岐
        if self.magic_info.magic_layer == MagicLayer.LAYER_1_REQUEST_GEN:
            # レイヤ１専用のプロンプトを使用
            compiler_path = GrimoireUtil.get_valid_compiler("general_prompt.md")
            log("レイヤ１専用のプロンプト: %s", compiler_path)

        # grimoire_compiler更新
        self.magic_info.grimoire_compiler = compiler_path
        log("grimoire_compilerを更新しました。 %s", self.magic_info.grimoire_compiler)

    @log_inout
    def handle_existing_target_file(self) -> str:
        """ターゲットファイルが存在する場合の処理

        Returns:
            str: 処理結果のファイルパス
        """
        file_info = self.magic_info.file_info
        log(f"{file_info.source_file_path}の変更を検知しました。")
        if os.path.exists(file_info.past_source_file_path):
            return self.update_target_file_from_source_diff()
        return self.update_target_file_propose_and_apply(file_info.target_file_path, self.magic_info.prompt)

    # ソースファイルの差分比率のしきい値（超えると差分では処理できないので再作成）
    SOURCE_DIFF_RATIO_THREADHOLD = 0.1

    @log_inout
    def update_target_file_from_source_diff(self) -> str:
        """ターゲットファイルをソースファイルの差分から更新する処理

        Returns:
            str: 処理結果のファイルパス
        """
        file_info = self.magic_info.file_info
        import difflib

        old_source_lines = FileUtil.read_file(file_info.past_source_file_path)
        new_source_lines = FileUtil.read_file(file_info.source_file_path)

        source_diff = difflib.unified_diff(old_source_lines, new_source_lines, lineterm="", n=0)
        source_diff_text = "".join(source_diff)
        log(f"source_diff_text={source_diff_text}")

        # source差分比率を計算
        source_diff_ratio = len(source_diff_text) / len(new_source_lines)
        log("source_dsource_diff_ratio=%f", source_diff_ratio)

        # source_diffを加味したプロンプト(prompt_diff)を作成
        prompt_diff = "\n<<最新の作業指示>>\n" + new_source_lines
        if source_diff_text == "":
            # 差分がない
            log("ソースファイルの差分がないため再適用します。")
        elif source_diff_ratio > BaseConverter.SOURCE_DIFF_RATIO_THREADHOLD:
            # 差分が大きすぎる
            log("ソースファイルの差分が大きいためターゲットファイルを再作成します。")
            return self.handle_new_target_file()
        else:
            # (通常処理)差分をプロンプトに追加
            prompt_diff += "\n\n<<(注意)重要な変化点(注意)>>\n"
            prompt_diff += source_diff_text
        self.magic_info.prompt_diff = prompt_diff

        return self.update_target_file_propose_and_apply(file_info.target_file_path, self.magic_info.prompt_diff)

    def update_target_file_propose_and_apply(self, target_file_path, prompt=None) -> str:
        """
        ターゲットファイルの変更差分を提案して適用する関数

        Args:
            target_file_path (str): 現在のターゲットファイルのパス
            prompt (str): ソースファイルの差分などターゲットファイルに適用するべき作業指示を含むprompt
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
        self.magic_info.prompt_diff = prompt
        response = litellm.generate_response(
            model=settings.model_name_lite,
            prompt=prompt,
            max_tokens=1000,
            temperature=0.0,
        )
        target_diff = response.strip()
        # ターゲットファイルの差分を表示
        log("ターゲットファイルの差分(冒頭100字):")
        log(target_diff[:100])

        # ユーザーに適用方法を尋ねる
        log("差分をどのように適用しますか?")
        log("1. AIで適用する")
        choice = "1"

        while True:
            if choice == "1":
                # 差分をターゲットファイルに自動で適用
                self.apply_diff_to_target_file(target_file_path, target_diff)
                log(f"{target_file_path}に差分を自動で適用しました。")
                break
            log_e("論理異常： choice=%d", choice)
            choice = "1"

        return target_file_path

    @log_inout
    def apply_diff_to_target_file(self, target_file_path: str, target_diff: str) -> str:
        """
        提案された差分をターゲットファイルに適用する関数

        Args:
            target_file_path (str): ターゲットファイルのパス
            target_diff (str): 適用する差分
        """
        # ターゲットファイルの現在の内容を読み込む
        current_content = FileUtil.read_file(target_file_path)

        # プロンプトを作成してAPIに送信し、修正された内容を取得
        prompt_apply = f"""
現在のターゲットファイルの内容:
{current_content}
上記のターゲットファイルの内容に対して、以下のUnified diff 適用後のターゲットファイルの内容を生成してください。

例)
変更前
- graph.node(week_node_name, shape='box', style='filled', fillcolor='#FFCCCC')

変更後
+ graph.node(week_node_name, shape='box', style='filled', fillcolor='#CCCCFF')

番号など変わった場合は振り直しもお願いします。

提案された差分:
{target_diff}

        """

        self.magic_info.prompt_apply = prompt_apply
        modified_content = litellm.generate_response(settings.model_name, prompt_apply, 2000, 0.3)

        # 修正後の内容をターゲットファイルに書き込む
        new_target_file_path = FileUtil.write_file(target_file_path, modified_content)

        log(f"{new_target_file_path}に修正を適用しました。")
        return new_target_file_path

    @log_inout
    def handle_new_target_file(self):
        file_info = self.magic_info.file_info
        log(f"""
{file_info.target_file_path}は新しいファイルです。少々お時間をいただきます。
{file_info.source_file_path} -> {file_info.target_file_path}
                  """)

        return generate_md_from_prompt(self.magic_info)


if __name__ == "__main__":  # このスクリプトが直接実行された場合にのみ、以下のコードを実行します。
    magic_workflow = MagicWorkflow()
    converter = BaseConverter(magic_workflow)
    converter.convert()
