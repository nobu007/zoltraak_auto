import os

import zoltraak.llms.litellm_api as litellm
from zoltraak import settings
from zoltraak.core.magic_workflow import MagicWorkflow
from zoltraak.core.prompt_manager import PromptEnum
from zoltraak.gen_markdown import generate_md_from_prompt, prepare_prompt_final
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
        request_file_path
        structure_file_path
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
            self.magic_info.prompt_goal = self.magic_info.prompt_input
            if file_info.source_file_path != file_info.target_file_path:
                # ソースファイルとターゲットファイルが異なる場合のみ、ソースファイルの指示を追加
                self.magic_info.prompt_goal += "\n\n<<追加指示>>\n"
                self.magic_info.prompt_goal += FileUtil.read_file(file_info.source_file_path)
        else:
            # ソースファイルを保存(設計では初回のprompt_file_pathにだけ保存する)
            log(f"既存のソースファイル {file_info.source_file_path} が無効なのでプロンプトを保存します。")
            FileUtil.write_file(file_info.source_file_path, self.magic_info.prompt_input)

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
            self.magic_info.prompt_input = ""
        elif self.magic_info.magic_mode is MagicMode.GRIMOIRE_AND_PROMPT:
            # グリモアまたはプロンプトどちらか TODO: 用語をコンパイラに統一したい
            if not os.path.isfile(compiler_path):
                compiler_path = ""
                if not self.magic_info.prompt_input:
                    log("コンパイラもプロンプトも未設定のため、一般的なプロンプトを使用します。")
                    compiler_path = ""
                    self.magic_info.prompt_input = FileUtil.read_grimoire(default_compiler_path)
        elif self.magic_info.magic_mode is MagicMode.PROMPT_ONLY:
            # プロンプトのみ
            compiler_path = ""
            if not self.magic_info.prompt_input:
                log("プロンプトが未設定のため、一般的なプロンプトを使用します。")
                self.magic_info.prompt_input = FileUtil.read_grimoire(default_compiler_path)
        else:
            # SEARCH_GRIMOIRE or ZOLTRAAK_LEGACY(ノーケア、別のところで処理すること！)
            log("(SEARCH_GRIMOIRE)一般的なプロンプトを使用します。")
            if not os.path.isfile(compiler_path):
                compiler_path = default_compiler_path
                self.magic_info.prompt_input = FileUtil.read_grimoire(default_compiler_path)

        # grimoire_compiler更新
        self.magic_info.grimoire_compiler = compiler_path
        log("grimoire_compilerを更新しました。 %s", self.magic_info.grimoire_compiler)

        # prompt_finalを更新
        prepare_prompt_final(self.magic_info)

    @log_inout
    def update_grimoire_and_prompt_by_layer(self):
        # レイヤによる分岐
        if self.magic_info.magic_layer == MagicLayer.LAYER_1_REQUEST_GEN:
            # レイヤ1専用のプロンプトを使用
            compiler_path = GrimoireUtil.get_valid_compiler("general_prompt.md")
            log("レイヤ1専用のプロンプト: %s", compiler_path)
        if self.magic_info.magic_layer == MagicLayer.LAYER_2_REQUIREMENT_GEN:
            # レイヤ2専用のプロンプトを使用
            compiler_path = GrimoireUtil.get_valid_compiler("structure_full.md")
            log("レイヤ2専用のプロンプト: %s", compiler_path)

    @log_inout
    def handle_existing_target_file(self) -> str:
        """ターゲットファイルが存在する場合の処理

        Returns:
            str: 処理結果のファイルパス
        """
        file_info = self.magic_info.file_info
        if self.magic_workflow.prompt_manager.is_same_prompt(PromptEnum.FINAL):  # -- 前回と同じプロンプトの場合
            log(f"スキップ(既存＆input変更なし): {file_info.target_file_path}")
            return self.magic_info.file_info.target_file_path  # --- 処理をスキップし既存のターゲットファイルを返す

        log(f"{file_info.target_file_path}を更新します。")
        if os.path.exists(file_info.past_source_file_path):
            log(f"{file_info.source_file_path}の差分から更新リクエストを生成中・・・")
            return self.update_target_file_from_source_diff()
        log("プロンプトから更新リクエストを生成中・・・")
        return self.update_target_file_propose_and_apply(file_info.target_file_path, self.magic_info.prompt_input)

    # ソースファイルの差分比率のしきい値（超えると差分では処理できないので再作成）
    SOURCE_DIFF_RATIO_THRESHOLD = 0.1

    # match_rateのしきい値（未満なら再作成）
    MATCH_RATE_THRESHOLD = 50

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
        old_target_lines = FileUtil.read_file(file_info.past_target_file_path)

        source_diff = difflib.unified_diff(old_source_lines, new_source_lines, lineterm="", n=0)
        source_diff_text = "".join(source_diff)
        log(f"source_diff_text={source_diff_text}")

        # source差分比率を計算
        source_diff_ratio = 1.0
        if len(new_source_lines) > 0:
            source_diff_ratio = len(source_diff_text) / len(new_source_lines)
            log("source_diff_ratio=%f", source_diff_ratio)

        # source_diffを加味したプロンプト(prompt_diff)を作成
        prompt_diff_order = "\n<<最新の作業指示>>\n" + new_source_lines
        if source_diff_ratio > BaseConverter.SOURCE_DIFF_RATIO_THRESHOLD:
            # 差分が大きすぎる
            log("ソースファイルの差分が大きいためターゲットファイルを再作成します。")
            return self.handle_new_target_file()
        if (
            self.get_match_rate_source_and_target_file(old_target_lines, new_source_lines)
            < BaseConverter.MATCH_RATE_THRESHOLD
        ):
            # match_rateが低すぎる
            log("MATCH_RATE_THRESHOLD に満たないためターゲットファイルを再作成します。")
            return self.handle_new_target_file()

        # source_diffを加味したプロンプト(prompt_diff)を作成
        prompt_diff_order = "\n<<最新の作業指示>>\n" + new_source_lines
        if source_diff_text:
            prompt_diff_order += "\n\n<<(注意)重要な変化点(注意)>>\n"
            prompt_diff_order += source_diff_text
        else:
            # 差分がない場合はスキップ
            log("source_diff_textが空のため、target_fileを更新しません。")
            return file_info.target_file_path
        self.magic_info.prompt_diff_order = prompt_diff_order

        return self.update_target_file_propose_and_apply(file_info.target_file_path, prompt_diff_order)

    def get_match_rate_source_and_target_file(self, old_target_lines: str, new_source_lines: str) -> int:
        """
        最新のソースファイルと前回のターゲットファイルの適合性を[0-100]のスコアで返します。100が完全適合です。

        Args:
            old_target_lines (str): 前回のターゲットファイルの内容
            new_source_lines (str): 今回のソースファイルの内容
        """

        prompt_match_rate = f"""
あなたは優秀なプログラマーです。前回のターゲットファイルの内容と今回のソースファイルの内容を示します。
今回のターゲットファイルを再作成するべきか判断したいです。

そのために、前回のターゲットファイルの内容が今回のソースファイルの内容に適合するかどうかを[0-100]のint値のスコアで判定してください。
0  ：完全に適合しない⇒ターゲットファイルの再作成が必要
30 ：適合度が低い⇒前回のターゲットファイルを破棄して再作成が望ましい
80 ：適合度が高い⇒前回のターゲットファイルをベースに差分修正が望ましい
100：完全適合⇒前回のターゲットファイルの内容から変更の必要なし

注意点：
・ファイルにdiffやunified diff形式のデータが含まれている場合は適合度が低いと判断してください。
・ソースファイルとターゲットファイルの関係性が適切でない場合も適合度が低いと判断してください。

回答は数値[0-100]のみでお願いします。

それではファイル内容を示します。

前回のターゲットファイルの内容:
{old_target_lines}

今回のソースファイルの内容:
{new_source_lines}

        """
        self.magic_info.prompt_match_rate = prompt_match_rate
        response = litellm.generate_response(
            model=settings.model_name_lite,
            prompt=prompt_match_rate,
            max_tokens=settings.max_tokens_get_match_rate,
            temperature=0.0,
        )
        match_rate = response.strip()
        # ターゲットファイルの差分を表示
        log("match_rate=%s", match_rate)

        try:
            match_rate = int(match_rate)
        except ValueError:
            log_e("match_rateの取得失敗： match_rate=%s", match_rate)
            match_rate = 0
        return match_rate

    def update_target_file_propose_and_apply(self, target_file_path: str, prompt_diff_order: str) -> str:
        """
        ターゲットファイルの変更差分を提案して適用する関数

        Args:
            target_file_path (str): 現在のターゲットファイルのパス
            prompt_diff_order (str): ソースファイルの差分などターゲットファイルに適用するべき作業指示を含むprompt
        """
        # プロンプトにターゲットファイルの内容を変数として追加
        current_target_code = FileUtil.read_file(target_file_path)

        prompt_diff = f"""
以下の指示に従って、ターゲットファイルの変更案を作成してください。
手順
　1. 現在のターゲットファイルの内容を確認してください。
  2. 変更内容(依頼内容)を確認してください。
  3. 基本的に現在の内容を尊重して情報を追加する方向で検討してください。
  4. ターゲットファイルの変更が必要な部分"のみ"をunified diff形式で出力してください。他の出力は一切不要です。

現在のターゲットファイルの内容:
{current_target_code}

変更内容(依頼内容):
{prompt_diff_order}

出力内容指示(再掲):
ターゲットファイルの変更が必要な部分"のみ"をプログラムで出力してください。
出力はunified diff形式で、削除した文を-、追加した文を+にします。
前後のn指定(ファイル単位で固定)はユニークな部分を識別するために必要な範囲を抽出してください。


例)
@@ -1,4 +1,4 @@
 line1
-line2
+line2 modified
 line3
-line4
+line4 modified

        """
        self.magic_info.prompt_diff = prompt_diff
        response = litellm.generate_response(
            model=settings.model_name_lite,
            prompt=prompt_diff,
            max_tokens=settings.max_tokens_propose_diff,
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

上記のターゲットファイルの内容に対して、以下のUnified diff 形式で提案された差分が分かっています。
差分適用後に不備や不要部分がなくなった最終的なターゲットファイルの内容だけを生成してください。
番号など変わった場合は振り直しもお願いします。

提案された差分:
{target_diff}

        """

        self.magic_info.prompt_apply = prompt_apply
        modified_content = litellm.generate_response(
            settings.model_name, prompt_apply, settings.max_tokens_apply_diff, 0.3
        )

        # 修正後の内容をターゲットファイルに書き込む
        new_target_file_path = FileUtil.write_file(target_file_path, modified_content)

        log(f"{new_target_file_path}に修正を適用しました。")
        return new_target_file_path

    @log_inout
    def handle_new_target_file(self):
        file_info = self.magic_info.file_info
        log(f"""
要件定義書執筆中: {file_info.target_file_path}は新しいファイルです。少々お時間をいただきます。
{file_info.source_file_path} -> {file_info.target_file_path}
                  """)
        return generate_md_from_prompt(self.magic_info)


if __name__ == "__main__":  # このスクリプトが直接実行された場合にのみ、以下のコードを実行します。
    magic_workflow = MagicWorkflow()
    converter = BaseConverter(magic_workflow)
    converter.convert()
