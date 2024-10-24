import os

from tests.unit_tests.helper import BaseTestCase


class TestZoltraakCommand(BaseTestCase):  # TestZoltraakCommand クラスを定義し、 BaseTestCaseを継承します。
    def setUp(self):
        # super().setUp() # BaseTestCaseのsetUpメソッドを無効化（llm呼び出しを使って試験）

        # ディレクトリのパスを設定
        self.zoltraak_auto_dir = os.path.join(os.path.dirname(__file__), "../..")
        self.zoltraak_auto_dir = os.path.abspath(self.zoltraak_auto_dir)
        self.prompt_input_path = os.path.join(self.zoltraak_auto_dir, "InstantPromptBox", "README_JA.md")
        self.work_dir = os.path.join(self.zoltraak_auto_dir, "work")
        os.makedirs(self.work_dir, exist_ok=True)

    def tearDown(self):
        # 終了時の処理を記述
        pass

    def test_data_quality_evaluation(self):
        """
        zoltraakコマンドに実データを入力して出力内容の精度や評価を確認します。
        """
        # TODO: テスト追加
