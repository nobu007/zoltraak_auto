import os
import sys
import unittest

from tests.unit_tests.helper import BaseTestCase
from zoltraak.cli import main
from zoltraak.converter.base_converter import BaseConverter
from zoltraak.core.magic_workflow import MagicWorkflow
from zoltraak.llms.litellm_api import generate_response
from zoltraak.utils.subprocess_util import SubprocessUtil

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(os.path.dirname(__file__), "../zoltraak"))
print("===============================")

# モック用の定義
# 1. モジュールのインポート方法に応じたモックの定義(bb.xxを置き換える例):
#    a. from import文を使用する場合:
#       例: cc.pyで「from aa import bb」としてbb.xxを使用する場合
#       MOCK_DEFINITION = "cc.bb.xx" <= "aa.bb.xx"ではない
#    b. import文を使用する場合:
#       例: aa.pyで「import bb」としてbb.xxを使用する場合
#       MOCK_DEFINITION = "aa.bb.xx"
# 2. 命名規約
#    a. MOCK_(関数名): 単独のテストだけに使用するモック
#    a. ALL_MOCK_(関数名)： 全てのテストで使用するモック
MOCK_CLI_MAIN_EXEC = "zoltraak.cli.main_exec"

# キーワード定義
CANONICAL_NAME_KEYWORD = "zoltraak end canonical_name: sample"
DUMMY_CONTENTS = "# Test File\nThis is a test file.\n# HASH: e32c2339" * 10


class TestZoltraakCommand(BaseTestCase):  # TestZoltraakCommand クラスを定義し、 BaseTestCaseを継承します。
    def setUp(self):
        super().setUp()
        self.set_up_files()

    def set_up_files(self):
        # テスト全体で使用するファイルのセットアップ
        with open("test_file.md", "w", encoding="utf-8") as f:
            f.write("test_file.md\n" + DUMMY_CONTENTS)

    def test_zoltraak_command(self):
        """
        zoltraakコマンドの機能をテストします。

        このテストでは、以下の項目を確認します:
        1. mdファイルの引数を指定した場合、正常に実行されること。
        2. -pオプションでプロンプトを指定した場合、正常に実行されること。
        3. -cオプションでコンパイラを指定した場合、正常に実行されること。
        4. -fオプションでフォーマッタを指定した場合、正常に実行されること。
        5. --helpオプションを指定した場合、ヘルプメッセージが表示されること。
        6. --versionオプションを指定した場合、バージョン情報が表示されること。

        実行例:
        - `zoltraak sample.md` : sample.mdファイルを入力として実行
        - `zoltraak "サンプルテキスト" -p "サンプルプロンプト" -c compiler.md -f formatter.md`
           サンプルテキストを入力として、指定したプロンプト、コンパイラ、フォーマッタを使用して実行
        - `zoltraak --help` : ヘルプメッセージを表示
        - `zoltraak --version` : バージョン情報を表示
        """
        # mock
        self.set_mock_return_value(MOCK_CLI_MAIN_EXEC)

        # mdファイルの引数を指定したテスト
        sample_input = os.path.join(os.path.dirname(__file__), "sample.md")
        sys.argv = ["zoltraak", sample_input]
        main()
        # TODO: チェック追加とメンテナンス
        # self.assertIn("サンプルプロンプト", result)

        # -pオプションでプロンプトを指定したテスト
        # TODO: test_prompt_argument()と重複しているので統一する
        # result = SubprocessUtil.run(
        #     ["zoltraak", "sample.md", "-p", "サンプルプロンプト"], capture_output=True, text=True
        # )
        # self.assertEqual(result.returncode, 0)
        # self.assertIn("sample.md", result.stdout)
        # self.assertIn("サンプルプロンプト", result.stdout)

        # # -cオプションでコンパイラを指定したテスト
        # result = SubprocessUtil.run(["zoltraak", "sample.md", "-c", "dev_obj.md"], capture_output=True, text=True)
        # self.assertEqual(result.returncode, 0)
        # self.assertIn("sample.md", result.stdout)
        # self.assertIn("dev_obj.md", result.stdout)

        # # -fオプションでフォーマッタを指定したテスト
        # result = SubprocessUtil.run(["zoltraak", "sample.md", "-f", "md_comment.md"], capture_output=True, text=True)
        # self.assertEqual(result.returncode, 0)
        # self.assertIn("sample.md", result.stdout)
        # self.assertIn("formatter.md", result.stdout)

        # # --helpオプションを指定したテスト
        # result = SubprocessUtil.run(["zoltraak", "--help"], capture_output=True, text=True)
        # self.assertEqual(result.returncode, 0)
        # self.assertIn("使用方法:", result.stdout)

        # # --versionオプションを指定したテスト
        # result = SubprocessUtil.run(["zoltraak", "--version"], capture_output=True, text=True)
        # self.assertEqual(result.returncode, 0)
        # self.assertIn("zoltraak version", result.stdout)

    def test_zoltraak_sample(self):
        """
        zoltraakコマンドの本機能をサンプル実行でテストします。

        このテストでは、以下の項目を確認します:
        1. mdファイルの引数を指定した場合、正常に実行されること。

        実行例:
        - `zoltraak sample.md` : sample.mdファイルを入力として実行
        """
        # mdファイルの引数を指定したテスト
        sample_input = os.path.join(os.path.dirname(__file__), "tests", "sample.md")
        result = SubprocessUtil.run(["zoltraak", sample_input], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn(CANONICAL_NAME_KEYWORD, result.stdout)

    def test_missing_md_file_argument(self):  # mdファイルの引数がない場合のテストメソッドを定義します.
        """
        zoltraakコマンドをmdファイルの引数なしで実行した場合、正しいエラーメッセージが表示されることを確認します。
        実行例: `zoltraak` コマンドを引数なしで実行した場合、"エラー: 入力ファイルまたはテキストが指定されていません。"
        というエラーメッセージが表示されるべきです。
        """
        result = SubprocessUtil.run(
            ["zoltraak"], capture_output=True, text=True, check=False
        )  # zoltraakコマンドを引数なしで実行し、その結果をresultに格納します。
        print("STDOUT:", result.stdout)  # 標準出力の内容を出力
        print("STDERR:", result.stderr)  # 標準エラーの内容を出力

        self.assertEqual(result.returncode, 1)  # リターンコードが1（エラー）であることを確認
        self.assertNotEqual(result.stdout, "")  # 標準出力が空でないことを確認

    def test_prompt_argument(self):  # プロンプト引数のテストメソッドを定義します。
        """
        zoltraakコマンドに-pオプションでプロンプトを指定した場合、正常に実行されることを確認します。
        実行例: `zoltraak calc.md -p "足し算のプログラムを書きたい"` コマンドを実行した場合、
        エラーが発生せずに正常に終了するはずです。
        """
        result = SubprocessUtil.run(
            ["zoltraak", "test_file.md", "-p", "足し算のプログラムを書きたい"],
            capture_output=True,
            text=True,
            check=False,
        )  # zoltraakコマンドを-pオプションでプロンプトを指定して実行し、その結果をresultに格納します。
        print("STDOUT:", result.stdout)  # 標準出力の内容を出力
        print("STDERR:", result.stderr)  # 標準エラーの内容を出力
        self.assertEqual(result.returncode, 0)  # resultのリターンコードが0（正常終了）であることを確認します。
        self.assertEqual(result.stderr, "")  # result.stderrが空文字列（エラーメッセージなし）であることを確認します。

        os.remove("test_file.md")

    def test_text_input(self):
        """
        zoltraakコマンドにテキスト入力を与えた場合のテストメソッドを定義します。
        実行例: `zoltraak "お腹減ったから短いプログラムで解決して"` コマンドを実行した場合、
        エラーが発生せずに正常に終了するはずです。
        """
        result = SubprocessUtil.run(
            ["zoltraak", "お腹減ったから短いプログラムで解決して"], capture_output=True, text=True, check=False
        )  # zoltraakコマンドにテキスト入力を与えて実行し、その結果をresultに格納します。
        print("STDOUT:", result.stdout)  # 標準出力の内容を出力
        print("STDERR:", result.stderr)  # 標準エラーの内容を出力

        self.assertEqual(result.returncode, 0)  # resultのリターンコードが0（正常終了）であることを確認します。
        self.assertEqual(result.stderr, "")  # result.stderrが空文字列（エラーメッセージなし）であることを確認します。


class TestCompilerFunctionality(BaseTestCase):  # クラス名をTestCompilerFunctionalityに変更
    """
    各コンパイラの機能をテストするクラス

    このクラスでは、以下のコンパイラの機能をテストします:
    - biz_consult_copy.md: ビジネスコンサルティングドキュメントのコピーを生成するコンパイラ
    - biz_consult.md: ビジネスコンサルティングドキュメントを生成するコンパイラ
    - dev_akirapp.md: アプリ開発の手引きを生成するコンパイラ
    - dev_front.md: フロントエンド開発のドキュメントを生成するコンパイラ
    - dev_func.md: 機能開発のドキュメントを生成するコンパイラ
    - dev_obj.md: オブジェクト指向設計のドキュメントを生成するコンパイラ

    各テストメソッドでは、コンパイラのパス、ゴールプロンプト、期待される出力ファイルのパスを指定し、
    run_compiler_testメソッドを呼び出してコンパイラの機能をテストします。
    """

    def setUp(self):
        # TODO: 生成物をちゃんとチェックするならコメントアウトしてモックを無効化する必要あり
        super().setUp()

        self.magic_workflow = MagicWorkflow()
        self.magic_info = self.magic_workflow.magic_info
        self.magic_info.file_info.update_source_target("pre.md", "output.md")
        self.magic_info.update()
        self.prompt_manager = self.magic_workflow.prompt_manager

    def test_biz_consult_copy_compiler(self):
        """
        biz_consult_copy.mdコンパイラの機能をテストする
        """
        compiler_path = "biz_consult_copy.md"
        goal_prompt = "今月中にビジネスコンサルティングドキュメントを作成する"
        expected_md_path = "def_work_book_1.md"
        self.run_compiler_test(compiler_path, goal_prompt, expected_md_path)

    def test_biz_consult_compiler(self):
        """
        biz_consult.mdコンパイラの機能をテストする
        """
        compiler_path = "biz_consult.md"
        goal_prompt = "今月中にビジネスコンサルティングドキュメントを作成する"
        expected_md_path = "def_work_book_2.md"
        self.run_compiler_test(compiler_path, goal_prompt, expected_md_path)

    def test_dev_akirapp_compiler(self):
        """
        dev_akirapp.mdコンパイラの機能をテストする
        """
        compiler_path = "dev_akirapp.md"
        goal_prompt = "今月中にアプリ開発の手引きを書く"
        expected_md_path = "def_akirapp.md"
        self.run_compiler_test(compiler_path, goal_prompt, expected_md_path)

    def test_dev_front_compiler(self):
        """
        dev_front.mdコンパイラの機能をテストする
        """
        compiler_path = "dev_front.md"
        goal_prompt = "今月中にLPのフロントエンドを完成させる"
        expected_md_path = "def_front.md"
        self.run_compiler_test(compiler_path, goal_prompt, expected_md_path)

    def test_dev_func_compiler(self):
        """
        dev_func.mdコンパイラの機能をテストする
        """
        compiler_path = "dev_func.md"
        goal_prompt = "Manimを用いたMoE(Mixture of experts)のプログラムを書く"
        expected_md_path = "def_moe.md"
        self.run_compiler_test(compiler_path, goal_prompt, expected_md_path)

    def test_dev_obj_compiler(self):
        """
        dev_obj.mdコンパイラの機能をテストする
        """
        compiler_path = "dev_obj.md"
        goal_prompt = "今月中にオブジェクト指向設計を用いた在庫管理システムを開発する"
        expected_md_path = "def_inventory.md"
        self.run_compiler_test(compiler_path, goal_prompt, expected_md_path)

    def test_dev_obj_lisp_compiler(self):
        """
        dev_obj_lisp.mdコンパイラの機能をテストする
        """
        compiler_path = "dev_obj_lisp.md"
        goal_prompt = "今月中に金融リスク分析プロジェクトを完了させる"
        expected_md_path = "def_risk_analysis.md"
        self.run_compiler_test(compiler_path, goal_prompt, expected_md_path)

    def test_dev_obj_lisp_g_compiler(self):
        """
        dev_obj_lisp_g.mdコンパイラの機能をテストする
        """
        compiler_path = "dev_obj_lisp_g.md"
        goal_prompt = "今月中にジェネリックプログラミングを活用した医療データ解析基盤を構築する"
        expected_md_path = "def_medical_data.md"
        self.run_compiler_test(compiler_path, goal_prompt, expected_md_path)

    def test_dev_obj_lisp_g_base64_compiler(self):
        """
        dev_obj_lisp_g_base64.mdコンパイラの機能をテストする
        """
        compiler_path = "dev_obj_lisp_g_base64.md"
        goal_prompt = "今月中に医療企業向け機密情報管理ツールを実装する"
        expected_md_path = "def_confidential_info.md"
        self.run_compiler_test(compiler_path, goal_prompt, expected_md_path)

    def test_encode_lisp_compiler(self):
        """
        encode_lisp.mdコンパイラの機能をテストする
        """
        compiler_path = "encode_lisp.md"
        goal_prompt = "今月中に暗号化通信システムを開発する"
        expected_md_path = "def_encrypted_comm.md"
        self.run_compiler_test(compiler_path, goal_prompt, expected_md_path)

    def test_general_def_compiler(self):
        """
        general_def.mdコンパイラの機能をテストする
        """
        compiler_path = "general_def.md"
        goal_prompt = "今月中に拡張現実（AR）アプリケーションを開発する"
        expected_md_path = "def_ar_app.md"
        self.run_compiler_test(compiler_path, goal_prompt, expected_md_path)

    def test_general_reqdef_compiler(self):
        """
        general_reqdef.mdコンパイラの機能をテストする
        """
        compiler_path = "general_reqdef.md"
        goal_prompt = "今月中に政府向けの少子化対策提言書を執筆する"
        expected_md_path = "def_proposal.md"
        self.run_compiler_test(compiler_path, goal_prompt, expected_md_path)

    def run_compiler_test(self, compiler_path, goal_prompt, expected_md_path, setting_dir="zoltraak/grimoires"):
        """
        指定されたコンパイラパスとプロンプトを使用してテストを実行する
        """

        # generate_md_from_prompt 関数を呼び出し、追加の引数を渡す
        self.magic_info.grimoire_compiler = f"{setting_dir}/compiler/{compiler_path}"
        self.magic_info.grimoire_formatter = f"{setting_dir}/formatter/None.md"
        self.magic_info.prompt_goal = goal_prompt
        self.magic_info.file_info.target_file_path = expected_md_path

        # 出力先をクリア
        if os.path.isfile(expected_md_path):
            os.remove(expected_md_path)

        # テストを実行
        self.prompt_manager.prepare_prompt_final(self.magic_info)
        base_converter = BaseConverter(self.magic_info, self.prompt_manager)
        base_converter.generate_md_from_prompt()

        self.check_generated_md_content(expected_md_path, compiler_path)  # 生成されたMDファイルの内容をチェックする
        self.move_generated_md_to_gomi(expected_md_path)  # 生成されたMDファイルをgomiディレクトリに移動する

    def check_generated_md_content(self, expected_md_path, compiler_path):
        """
        生成されたMDファイルの内容を確認する
        """
        with open(expected_md_path, encoding="utf-8") as f:
            generated_content = f.read()
        self.assertGreater(len(generated_content), 0, f"生成されたMDファイルが空です。 コンパイラパス: {compiler_path}")

    def move_generated_md_to_gomi(self, expected_md_path):
        """
        テスト後に生成されたMDファイルをgomiディレクトリに移動する

        Args:
            expected_md_path (str): 移動対象のMDファイルのパス
            open_file (bool): ファイルを開くかどうかのフラグ（デフォルトはFalse）
        """
        import datetime

        # Python 3.10でdatetime.UTCは存在しないので、datetime.timezone.utc を使う！
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")  # noqa: UP017
        gomi_dir = "gomi"
        if not os.path.exists(gomi_dir):
            os.makedirs(gomi_dir)
        new_file_path = os.path.join(gomi_dir, f"{timestamp}_{os.path.basename(expected_md_path)}")
        os.rename(expected_md_path, new_file_path)


class TestGenerateResponse(unittest.TestCase):
    def test_generate_response_anthropic(self):
        """
        Anthropicのモデルを使用してgenerate_response関数をテストする
        """
        anthropic_models = ["claude-3-opus-20240229", "claude-3-haiku-20240307", "claude-3-sonnet-20240229"]
        prompt = "これはテストプロンプトです。"

        for model_name in anthropic_models:
            response = generate_response(model_name, prompt)
            print(f"{model_name}からの応答: {response}")  # 応答内容を出力
            self.assertIsInstance(response, str, f"{model_name}からの応答が文字列ではありません")
            self.assertGreater(len(response), 0, f"{model_name}からの応答が空です")

    def test_generate_response_groq(self):
        """
        Groqのモデルを使用してgenerate_response関数をテストする
        """

        groq_models = [
            "groq/llama3-8b-8192",
            "groq/llama3-70b-8192",
            "groq/llama-3.1-8b-instant",
            "groq/mixtral-8x7b-32768",
            "groq/gemma2-9b-it",
        ]
        prompt = "これはテストプロンプトです。"

        for model_name in groq_models:
            response = generate_response(model_name, prompt)
            print(f"{model_name}からの応答: {response}")  # 応答内容を出力
            self.assertIsInstance(response, str, f"{model_name}からの応答が文字列ではありません")
            self.assertGreater(len(response), 0, f"{model_name}からの応答が空です")


if __name__ == "__main__":  # このスクリプトが直接実行された場合にのみ、以下のコードを実行します。
    # 全部を実行します
    unittest.main()  # unittestのmain関数を呼び出し、テストを実行します。
