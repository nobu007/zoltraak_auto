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
        os.makedirs(self.work_dir, exist_ok=True)

        # テスト開始時の時間を取得
        self.start_time = time.time()

        self.timeout_seconds = 600  # タイムアウト時間を設定
        self.end_time = 0.0  # 処理終了時間を初期化
        self.elapsed_time = 0.0  # 処理時間を初期化

    def tearDown(self):
        # 処理終了時間を記録
        self.end_time = time.time()
        self.elapsed_time = self.end_time - self.start_time

        # 処理時間を出力
        print(f"処理時間: {self.elapsed_time:.2f}秒")

        # タイムアウトを確認
        if self.elapsed_time > self.timeout_seconds:
            msg = f"処理が{self.timeout_seconds}秒以内に終了しませんでした。"
            raise TimeoutError(msg)

    def test_performance_first_run(self):
        """
        zoltraakコマンドに実データを入力して処理時間を確認します。
        """
        result = SubprocessUtil.run(
            ["zoltraak", "def_InstantPromptBox.md", "-p", self.prompt_input_path, "-ml", "4_", "-mle", "6_"],
            capture_output=True,
            text=True,
            check=False,
            cwd=self.work_dir,
        )
        print("STDOUT:", result.stdout)  # 標準出力の内容を出力
        print("STDERR:", result.stderr)  # 標準エラーの内容を出力
        self.assertEqual(result.returncode, 0)  # resultのリターンコードが0（正常終了）であることを確認します。
        self.assertEqual(result.stderr, "")  # result.stderrが空文字列（エラーメッセージなし）であることを確認します。
