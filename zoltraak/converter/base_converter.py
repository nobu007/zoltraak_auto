import os
from typing import ClassVar

from zoltraak import settings
from zoltraak.core.prompt_manager import PromptEnum, PromptManager
from zoltraak.gencode import TargetCodeGenerator
from zoltraak.schema.schema import EMPTY_CONTEXT_FILE, MagicInfo, MagicLayer, SourceTargetSet
from zoltraak.utils.diff_util import DiffUtil
from zoltraak.utils.file_util import FileUtil
from zoltraak.utils.log_util import log, log_change, log_e, log_head, log_inout
from zoltraak.utils.rich_console import generate_response_with_spinner


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

    呼び出し構成(通常):
        prepare()
        magic_workflow.pre_process()
        convert()
            -> handle_existing_target_file() or handle_new_target_file()
        magic_workflow.post_process()

    呼び出し構成(非同期版):
        prepare()
        prepare_generation(): 処理対象のlist[SourceTargetSet]を返す
        非同期で以下を並列実行
            magic_workflow.pre_process()
            convert()
                -> handle_existing_target_file() or handle_new_target_file()
            magic_workflow.post_process()
    """

    DEF_MAX_PROMPT_SIZE_FOR_DIFF = 5000  # 大きすぎるdiffは破綻しがちなので制限

    def __init__(self, magic_info: MagicInfo, prompt_manager: PromptManager):
        self.magic_info = magic_info
        self.prompt_manager = prompt_manager
        self.acceptable_layers = []
        self.name = "BaseConverter"
        self.source_target_set_list: list[SourceTargetSet] = []

    def prepare(self) -> None:
        """converter共通の初期化処理"""

        # context_file_pathを常にEMPTYで初期化する
        context_file_path = EMPTY_CONTEXT_FILE
        self.magic_info.file_info.context_file_path = context_file_path
        if not os.path.isfile(context_file_path):
            # 空のコンテキストファイルを保存(設計では初回だけデフォルトで保存する)
            log(f"コンテキストファイル更新(空):  {context_file_path}")
            FileUtil.write_file(context_file_path, "")

    def convert(self) -> str:
        """生成処理"""
        return self.convert_one()

    @log_inout
    def convert_one(self) -> str:
        """生成処理を１回実行する"""
        file_info = self.magic_info.file_info

        # ターゲットファイルの有無による分岐
        if FileUtil.has_content(file_info.target_file_path):  # ターゲットファイルが存在する場合
            return self.handle_existing_target_file()  # - 既存のターゲットファイルを処理
        # ターゲットファイルが存在しない場合
        return self.handle_new_target_file()  # - 新しいターゲットファイルを処理

    SKIP_LAYERS_BY_SOURCE: ClassVar[list[MagicLayer]] = [MagicLayer.LAYER_7_INFO_STRUCTURE_GEN]

    @log_inout
    def handle_existing_target_file(self) -> str:
        """ターゲットファイルが存在する場合の処理

        Returns:
            str: 処理結果のファイルパス
        """
        file_info = self.magic_info.file_info

        # 最終プロンプトによる分岐
        if self.prompt_manager.is_same_prompt(self.magic_info, PromptEnum.FINAL):  # -- 前回と同じプロンプトの場合
            log(f"スキップ(既存＆input変更なし): {file_info.target_file_path}")
            self.magic_info.history_info += " ->スキップ(既存＆input変更なし)"
            return file_info.target_file_path  # --- 処理をスキップし既存のターゲットファイルを返す

        # レイヤ個別のスキップ処理(要件定義書など複数inputで更新されるものはインプットの一致だけでスキップ)
        if self.magic_info.magic_layer in BaseConverter.SKIP_LAYERS_BY_SOURCE and self.is_same_source_as_past():
            log(f"スキップ(既存ソース): {file_info.target_file_path}")
            self.magic_info.history_info += " ->スキップ(既存＆input変更なし)"
            return file_info.target_file_path  # --- 処理をスキップし既存のターゲットファイルを返す

        # プロンプトの差分表示(デバッグ用)
        self.prompt_manager.show_diff_prompt(self.magic_info, PromptEnum.FINAL)

        log(f"{file_info.source_file_path}の差分から更新リクエストを生成中・・・")
        self.magic_info.history_info += " ->差分から更新"
        return self.update_target_file_from_source_diff()

    # ソースファイルの差分比率のしきい値（超えると差分では処理できないので再作成）
    SOURCE_DIFF_RATIO_THRESHOLD = 0.1

    # match_rateのしきい値
    MATCH_RATE_THRESHOLD_OK = 90  # 高いと処理スキップ(低いと差分適用)
    MATCH_RATE_THRESHOLD_NG = 50  # 低いと再作成

    # 差分計算に使える最低文字数のしきい値（未満なら再作成）
    VALID_CONTENT_THRESHOLD = 100

    def is_need_handle_new_target_file(
        self, old_source_content: str, new_source_content: str, source_diff: str
    ) -> bool:
        """ターゲットファイルをソースファイルの差分から更新する処理"""
        file_info = self.magic_info.file_info
        if len(old_source_content) < BaseConverter.VALID_CONTENT_THRESHOLD:
            # 前回ソースがない場合
            log(f"再作成(旧ソースなし): {file_info.target_file_path}")
            self.magic_info.history_info += " ->再作成(旧ソースなし)"
            return True

        if source_diff.strip() == "":
            # ソース差分なしの場合(=>コンテキストかプロンプトに差分あり)
            log(f"再作成(ソース差分なし): {file_info.target_file_path}")
            self.magic_info.history_info += " ->再作成(ソース差分なし)"
            return True

        log_head("ソースファイルの差分", source_diff, 300)

        # source差分比率を計算
        source_diff_ratio = 1.0
        if len(new_source_content) > 0:
            source_diff_ratio = len(source_diff) / len(new_source_content)
            log("source_diff_ratio=%f", source_diff_ratio)
        else:
            log_e("source_diff_ratioの計算失敗： len(new_source_lines)=%d", len(new_source_content))

        # source_diffを加味したプロンプト(prompt_diff)を作成
        if source_diff_ratio > BaseConverter.SOURCE_DIFF_RATIO_THRESHOLD:
            # 差分が大きすぎる
            log(f"再作成(ソース差分過大): {file_info.target_file_path}")
            self.magic_info.history_info += " ->再作成(ソース差分過大)"
            return True

        return False

    @log_inout
    def update_target_file_from_source_diff(self) -> str:
        """ターゲットファイルをソースファイルの差分から更新する処理

        Returns:
            str: 処理結果のファイルパス
        """
        file_info = self.magic_info.file_info

        old_source_content = FileUtil.read_file(file_info.past_source_file_path)
        new_source_content = FileUtil.read_file(file_info.source_file_path)
        old_target_content = FileUtil.read_file(file_info.past_target_file_path)
        source_diff = DiffUtil.diff0_ignore_space(old_source_content, new_source_content)

        if self.is_need_handle_new_target_file(old_source_content, new_source_content, source_diff):
            # 新規で再作成が必要な場合
            return self.handle_new_target_file()

        # 前回ターゲットと今回ソースの適合度判定
        prompt_final = PromptEnum.FINAL.get_current_prompt(self.magic_info)
        match_rate = self.get_match_rate_source_and_target_file(old_target_content, new_source_content, prompt_final)
        if match_rate >= BaseConverter.MATCH_RATE_THRESHOLD_OK:
            # 処理不要につきスキップ
            log("MATCH_RATE_THRESHOLD_OK 以上のためスキップします。")
            self.magic_info.history_info += f" ->スキップ(match_rate高={match_rate})"
            return self.handle_new_target_file()
        if match_rate < BaseConverter.MATCH_RATE_THRESHOLD_NG:
            # match_rateが低すぎる
            log("MATCH_RATE_THRESHOLD_NG に満たないためターゲットファイルを再作成します。")
            self.magic_info.history_info += f" ->再作成(match_rate不適合={match_rate})"
            return self.handle_new_target_file()
        # match_rateがMATCH_RATE_THRESHOLD_NG ～ MATCH_RATE_THRESHOLD_OK の場合は処理継続(差分適用モード)

        # source_diffを加味したプロンプト(prompt_diff)を作成
        prompt_diff_order = "\n<<最新の作業指示>>\n" + new_source_content
        prompt_diff_order += "\n\n<<(注意)重要な変化点(注意)>>\n"
        prompt_diff_order += source_diff

        # プロンプトサイズ制限
        if len(prompt_diff_order) > BaseConverter.DEF_MAX_PROMPT_SIZE_FOR_DIFF:
            log("prompt_diff_orderが大きすぎるため、target_fileを再作成します。")
            self.magic_info.history_info += " ->再作成(prompt_diff_order過大)"
            return self.handle_new_target_file()

        self.magic_info.prompt_diff_order = prompt_diff_order

        return self.update_target_file_propose_and_apply(file_info.target_file_path, prompt_diff_order)

    def get_match_rate_source_and_target_file(self, old_target_lines: str, new_source_lines: str, prompt: str) -> int:
        """
        最新のソースファイルと前回のターゲットファイルの適合性を[0-100]のスコアで返します。100が完全適合です。

        Args:
            old_target_lines: 前回のターゲットファイルの内容
            new_source_lines: 今回のソースファイルの内容
            prompt: 変換システムのプロンプト
        """

        prompt_match_rate = f"""
あなたは優秀なプロンプトエンジニアです。
ソースファイル⇒ターゲットファイルの変換システムにおいて、前回結果の妥当性判断をしてください。

下記の３つの情報を提示します。
・前回のターゲットファイルの内容(pre_source)
・今回のソースファイルの内容(source)
・変換システムのプロンプト(prompt)

今回のターゲットファイルの作成方法を（新規作成 or 差分作成 or 変更不要）から選択するための適合度を回答してください。
プロンプトエンジニアの見識を生かして、適切な判断をお願いします。

回答は以下を参考にして前回のターゲットファイルの内容が今回のソースファイルの内容＋変換システムのプロンプトと適合するかどうかを[0-100]のint値のスコアで判定してください。
0  ：完全に適合しない⇒ターゲットファイルの再作成が必要
30 ：適合度が低い⇒前回のターゲットファイルを破棄して再作成が望ましい
70 ：適合度が高い⇒前回のターゲットファイルをベースに差分修正が望ましい
100：完全適合⇒前回のターゲットファイルの内容から変更の必要なし

注意点：
・ファイルにdiffやunified diff形式のデータが含まれている場合は適合度が低いと判断してください。
・ソースファイルとターゲットファイルの関係性が適切でない場合も適合度が低いと判断してください。

回答は数値[0-100]のみでお願いします。

それではファイル内容を示します。

前回のターゲットファイルの内容:
<pre_source>
{old_target_lines}
</pre_source>

今回のソースファイルの内容:
<source>
{new_source_lines}
</source>

変換システムのプロンプト:
<prompt>
{prompt}
</prompt>

        """
        response = self.generate_response(
            prompt_enum=PromptEnum.MATCH_RATE,
            prompt=prompt_match_rate,
            max_tokens=settings.max_tokens_get_match_rate,
            temperature=settings.temperature_get_match_rate,
            model_name=settings.model_name_lite,
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
        response = self.generate_response(
            prompt_enum=PromptEnum.DIFF,
            prompt=prompt_diff,
            max_tokens=settings.max_tokens_propose_diff,
            temperature=settings.temperature_propose_diff,
            model_name=settings.model_name_lite,
        )
        target_diff = response.strip()
        # ターゲットファイルの差分を表示
        log_head("ターゲットファイルの差分", target_diff)

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
        modified_content = self.generate_response(
            prompt_enum=PromptEnum.APPLY,
            prompt=prompt_apply,
            max_tokens=settings.max_tokens_apply_diff,
            temperature=settings.temperature_apply_diff,
            model_name=settings.model_name,
        )

        # 修正後の内容をターゲットファイルに書き込む
        new_target_file_path = FileUtil.write_file(target_file_path, modified_content)

        log(f"{new_target_file_path}に修正を適用しました。")
        return new_target_file_path

    @log_inout
    def handle_new_target_file(self):
        """ターゲットファイル(md_fileまたはpy_file)を新規作成する"""
        file_info = self.magic_info.file_info
        log_change(
            f"新ファイル生成中:\n{file_info.target_file_path}は新しいファイルです。少々お時間をいただきます。",
            file_info.source_file_path,
            file_info.target_file_path,
        )
        self.magic_info.history_info += " ->新ファイル生成"
        if file_info.target_file_path.endswith(".py"):
            return self.handle_new_target_file_py()
        return self.generate_md_from_prompt()

    @log_inout
    def handle_new_target_file_py(self) -> str:
        """ソースコード(py_file)を新規作成する"""
        log("高級言語コンパイル中: ソースコード(py_file)を新規作成しています。")
        output_file_path = self.generate_py_from_prompt()

        log("ソースコード(py_file)を実行しています。")
        code = FileUtil.read_file(output_file_path)
        target = TargetCodeGenerator(self.magic_info)
        return target.process_generated_code(code)

    def is_same_source_as_past(self) -> bool:
        file_info = self.magic_info.file_info
        current_source_content = FileUtil.read_file(file_info.source_file_path)
        current_source_content = current_source_content.strip()
        past_source_content = FileUtil.read_file(file_info.past_source_file_path)
        past_source_content = past_source_content.strip()

        log("current_source_content(末尾100文字)=\n%s", current_source_content[-100:])
        log("past_source_content(末尾100文字)   =\n%s", past_source_content[-100:])
        return current_source_content == past_source_content

    def is_same_target_as_past(self) -> bool:
        file_info = self.magic_info.file_info
        current_target_content = FileUtil.read_file(file_info.target_file_path)
        current_target_content = current_target_content.strip()
        past_target_content = FileUtil.read_file(file_info.past_target_file_path)
        past_target_content = past_target_content.strip()

        log("current_target_content(末尾100文字)=\n%s", current_target_content[-100:])
        log("past_target_content(末尾100文字)   =\n%s", past_target_content[-100:])
        return current_target_content == past_target_content

    def generate_response(
        self,
        prompt_enum: PromptEnum,
        prompt: str,
        max_tokens: int = 4000,
        temperature: float = 0.0,
        model_name: str = settings.model_name,
    ) -> str:
        """ログ表示、プロンプトの保存、LLM呼び出し、結果の確認(TODO)をワンストップで実施する"""
        log("call prompt=%s", len(prompt))

        # プロンプトを保存
        prompt_enum.set_current_prompt(prompt, self.magic_info)

        # promptをファイルに保存
        self.save_prompt(prompt, prompt_enum)

        # LLM呼び出し
        response = generate_response_with_spinner(
            magic_info=self.magic_info,
            model_name=model_name,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        log("response=%s", len(response))

        return response

    def save_prompt(self, prompt: str, prompt_enum: PromptEnum) -> None:
        file_info = self.magic_info.file_info
        # プロンプトを magic_info に保存
        prompt_enum.set_current_prompt(prompt, self.magic_info)

        # work_dirからの相対パス取得
        target_file_path_rel = os.path.relpath(file_info.target_file_path, file_info.work_dir)

        # promptをファイルに保存
        self.prompt_manager.save_prompt(self.magic_info, prompt, target_file_path_rel, prompt_enum)

    def generate_md_from_prompt(self) -> str:
        """
        prompt_finalから任意のマークダウンファイルを生成する関数
        """
        response = self.generate_response(
            prompt_enum=PromptEnum.FINAL,
            prompt=self.magic_info.prompt_final,
            max_tokens=settings.max_tokens_generate_md,
            temperature=settings.temperature_generate_md,
            model_name=self.magic_info.model_name,
        )
        target_file_path = self.magic_info.file_info.target_file_path
        md_content = response.strip()  # 生成された要件定義書の内容を取得し、前後の空白を削除
        output_file_path = self.save_md_content(
            md_content, target_file_path
        )  # 生成された要件定義書の内容をファイルに保存
        self.print_generation_result(output_file_path)  # 生成結果を出力
        return output_file_path

    def generate_py_from_prompt(self) -> str:
        """
        prompt_finalから任意のpyファイルを生成する関数
        """
        code = self.generate_response(
            prompt_enum=PromptEnum.FINAL,
            prompt=self.magic_info.prompt_final,
            max_tokens=settings.max_tokens_generate_code,
            temperature=settings.temperature_generate_code,
            model_name=self.magic_info.model_name,
        )
        code = code.replace("```python", "").replace("```", "")
        return FileUtil.write_file(self.magic_info.file_info.target_file_path, code)

    def save_md_content(self, md_content, target_file_path) -> str:
        """
        生成された要件定義書の内容をファイルに保存する関数

        Args:
            md_content (str): 生成された要件定義書の内容
            target_file_path (str): 保存先のファイルパス
        """
        return FileUtil.write_grimoire(md_content, target_file_path)

    def print_generation_result(self, output_file_path):
        """
        要件定義書の生成結果を表示する関数

        Args:
            output_file_path (str): 生成された要件定義書のファイルパス
        """
        print()
        log(f"\033[32m魔法術式を構築しました: {output_file_path}\033[0m")  # 要件定義書の生成完了メッセージを緑色で表示

    def __str__(self) -> str:
        return f"{self.name}({self.magic_info.magic_layer})"

    def __repr__(self) -> str:
        return self.__str__()


if __name__ == "__main__":  # このスクリプトが直接実行された場合にのみ、以下のコードを実行します。
    magic_info_ = MagicInfo()
    prompt_manager_ = PromptManager()
    converter = BaseConverter(magic_info_, prompt_manager_)
    converter.convert()
