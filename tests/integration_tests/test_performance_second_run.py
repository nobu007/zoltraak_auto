import os
import time

from tests.unit_tests.helper import BaseTestCase
from zoltraak.utils.subprocess_util import SubprocessUtil


class TestZoltraakCommand(BaseTestCase):  # TestZoltraakCommand クラスを定義し、 BaseTestCaseを継承します。
    def setUp(self):
        # super().setUp() # BaseTestCaseのsetUpメソッドを無効化（llm呼び出しを使って試験）

        # ディレクトリのパスを設定
        self.zoltraak_auto_dir = os.path.join(os.path.dirname(__file__), "../..")
        self.zoltraak_auto_dir = os.path.abspath(self.zoltraak_auto_dir)
        self.prompt_input_path = os.path.join(self.zoltraak_auto_dir, "InstantPromptBox", "README_JA.md")
        self.work_dir = os.path.join(self.zoltraak_auto_dir, "work")

        # テスト開始時の時間を取得
        self.start_time = time.time()

        self.timeout_seconds = 5  # タイムアウト時間を設定
        self.end_time = 0.0  # 処理終了時間を初期化
        self.elapsed_time = 0.0  # 処理時間を初期化
        self.try_n = 1  # N回目の実行を保持する変数

    def tearDown(self):
        # 処理終了時間を記録
        self.end_time = time.time()
        self.elapsed_time = self.end_time - self.start_time

        # 処理時間を出力
        print(f"処理時間({self.try_n}回目): {self.elapsed_time:.2f}秒")

        # タイムアウトを確認
        if self.elapsed_time > self.timeout_seconds:
            msg = f"({self.try_n}回目) 処理が{self.timeout_seconds}秒以内に終了しませんでした。"
            raise TimeoutError(msg)

    def test_performance_second_run(self):
        """
        zoltraakコマンドに実データを入力して処理時間(2回目)を確認します。
        """

        # 1回目の実行
        result = SubprocessUtil.run(
            ["zoltraak", "def_InstantPromptBox.md", "-p", self.prompt_input_path, "-ml", "1_", "-mle", "4_"],
            capture_output=True,
            text=True,
            check=False,
            cwd=self.work_dir,
        )
        print("STDOUT(try1):", result.stdout)  # 標準出力の内容を出力
        print("STDERR(try1):", result.stderr)  # 標準エラーの内容を出力
        self.assertEqual(result.returncode, 0)  # resultのリターンコードが0（正常終了）であることを確認します。
        self.assertEqual(result.stderr, "")  # result.stderrが空文字列（エラーメッセージなし）であることを確認します。

        # テスト開始時の時間を取得
        self.start_time = time.time()
        self.try_n = 2

        # 2回目の実行
        result = SubprocessUtil.run(
            ["zoltraak", "def_InstantPromptBox.md", "-p", self.prompt_input_path, "-ml", "1_", "-mle", "4_"],
            capture_output=True,
            text=True,
            check=False,
            cwd=self.work_dir,
        )
        print("STDOUT(try2):", result.stdout)  # 標準出力の内容を出力
        print("STDERR(try2):", result.stderr)  # 標準エラーの内容を出力
        self.assertEqual(result.returncode, 0)  # resultのリターンコードが0（正常終了）であることを確認します。
        self.assertEqual(result.stderr, "")  # result.stderrが空文字列（エラーメッセージなし）であることを確認します。
