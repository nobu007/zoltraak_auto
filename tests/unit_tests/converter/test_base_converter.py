import os

from tests.unit_tests.helper import BaseTestCase
from zoltraak.converter.base_converter import BaseConverter
from zoltraak.core.magic_workflow import MagicWorkflow

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
ALL_MOCK_HANDLE_EXISTING_TARGET_FILE = "zoltraak.converter.base_converter.BaseConverter.handle_existing_target_file"
ALL_MOCK_UPDATE_TARGET_FILE_PROPOSE_AND_APPLY = (
    "zoltraak.converter.base_converter.BaseConverter.update_target_file_propose_and_apply"
)
ALL_MOCK_UPDATE_TARGET_FILE_FROM_SOURCE_DIFF = (
    "zoltraak.converter.base_converter.BaseConverter.update_target_file_from_source_diff"
)
MOCK_HANDLE_NEW_TARGET_FILE = "zoltraak.converter.base_converter.BaseConverter.handle_new_target_file"
MOCK_GENERATE_MD_FROM_PROMPT = "zoltraak.converter.base_converter.generate_md_from_prompt"

# キーワード定義
PROMPT_KEYWORD = "<<追加指示>>"
PROMPT_KEYWORD_NO_SOURCE = "zoltraakシステムは曖昧なユーザー入力を"
DUMMY_CONTENTS = "# Test File\nThis is a test file.\n# HASH: e32c2339" * 100


class TestBaseConverter(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.set_up_files()
        self.magic_workflow = MagicWorkflow()
        self.magic_info = self.magic_workflow.magic_info
        self.magic_info.file_info.update_source_target("pre.md", "output.md")
        self.magic_info.update()
        self.prompt_manager = self.magic_workflow.prompt_manager
        self.base_converter = BaseConverter(self.magic_info, self.prompt_manager)
        self.set_mock_return_value(ALL_MOCK_HANDLE_EXISTING_TARGET_FILE)
        self.set_mock_return_value(ALL_MOCK_UPDATE_TARGET_FILE_PROPOSE_AND_APPLY)
        self.set_mock_return_value(ALL_MOCK_UPDATE_TARGET_FILE_FROM_SOURCE_DIFF)

    def set_up_files(self):
        # テスト全体で使用するファイルのセットアップ
        os.makedirs("./past/source", exist_ok=True)
        with open("./past/source/pre.md", "w", encoding="utf-8") as f:
            f.write("past/source/pre.md\n" + DUMMY_CONTENTS)

        with open("./pre.md", "w", encoding="utf-8") as f:
            f.write("pre.md\n" + DUMMY_CONTENTS)

        with open("./output.md", "w", encoding="utf-8") as f:
            f.write("output.md\n" + DUMMY_CONTENTS)

    def tearDown(self):
        super().tearDown()
        print("tearDown")

    # =============  test_convert_one_source  ==============
    # source: True, target: True
    # -> handle_existing_target_file()が呼ばれる
    def test_convert_one_source_true_target_true(self):
        self.set_mock_return_value(MOCK_HANDLE_NEW_TARGET_FILE)
        result = self.base_converter.convert_one()
        self.assertEqual(result, "")
        self.check_mock_call_count(ALL_MOCK_HANDLE_EXISTING_TARGET_FILE, 1)
        self.check_mock_call_count(MOCK_HANDLE_NEW_TARGET_FILE, 0)
        self.assertIn(PROMPT_KEYWORD_NO_SOURCE, self.base_converter.magic_info.prompt_input)

    # source: False, target: True
    def test_convert_one_source_false_target_true(self):
        self.set_mock_return_value(MOCK_HANDLE_NEW_TARGET_FILE)
        os.remove("./pre.md")  # source ファイルを削除
        result = self.base_converter.convert_one()
        self.assertEqual(result, "")
        self.check_mock_call_count(ALL_MOCK_HANDLE_EXISTING_TARGET_FILE, 1)
        self.check_mock_call_count(MOCK_HANDLE_NEW_TARGET_FILE, 0)
        self.assertNotIn(PROMPT_KEYWORD, self.base_converter.magic_info.prompt_input)

    # source: True, target: False
    def test_convert_one_source_true_target_false(self):
        self.set_mock_return_value(MOCK_HANDLE_NEW_TARGET_FILE)
        os.remove("./output.md")  # target ファイルを削除
        result = self.base_converter.convert_one()
        self.assertEqual(result, "")
        self.check_mock_call_count(ALL_MOCK_HANDLE_EXISTING_TARGET_FILE, 0)
        self.check_mock_call_count(MOCK_HANDLE_NEW_TARGET_FILE, 1)
        self.assertIn(PROMPT_KEYWORD_NO_SOURCE, self.base_converter.magic_info.prompt_input)

    # source: False, target: False
    def test_convert_one_source_false_target_false(self):
        self.set_mock_return_value(MOCK_HANDLE_NEW_TARGET_FILE)
        os.remove("./pre.md")  # source ファイルを削除
        os.remove("./output.md")  # target ファイルを削除
        result = self.base_converter.convert_one()
        self.assertEqual(result, "")
        self.check_mock_call_count(ALL_MOCK_HANDLE_EXISTING_TARGET_FILE, 0)
        self.check_mock_call_count(MOCK_HANDLE_NEW_TARGET_FILE, 1)
        self.assertNotIn(PROMPT_KEYWORD, self.base_converter.magic_info.prompt_input)

    # =============  handle_existing_target_file  ==============

    # is_source_changed: True, past_source: True
    def test_handle_existing_target_file_source_true_past_true(self):
        result = self.base_converter.handle_existing_target_file()
        self.assertEqual(result, "")
        self.check_mock_call_count(ALL_MOCK_UPDATE_TARGET_FILE_FROM_SOURCE_DIFF, 0)
        self.check_mock_call_count(ALL_MOCK_UPDATE_TARGET_FILE_PROPOSE_AND_APPLY, 0)
        self.assertNotIn(PROMPT_KEYWORD, self.base_converter.magic_info.prompt_input)

    # =============  handle_new_target_file  ==============

    def test_handle_new_target_file(self):
        self.set_mock_return_value(MOCK_GENERATE_MD_FROM_PROMPT, return_value=PROMPT_KEYWORD)
        result = self.base_converter.handle_new_target_file()
        self.assertEqual(result, PROMPT_KEYWORD)
        self.check_mock_call_count_llm_generate_response(0)
