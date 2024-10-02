import os

from tests.unit_tests.helper import BaseTestCase
from zoltraak.converter.base_converter import BaseConverter
from zoltraak.schema.schema import MagicInfo

# モック用の定義
MOCK_HANDLE_EXISTING_TARGET_FILE = "zoltraak.converter.base_converter.BaseConverter.handle_existing_target_file"
MOCK_UPDATE_TARGET_FILE_PROPOSE_AND_APPLY = (
    "zoltraak.converter.base_converter.BaseConverter.update_target_file_propose_and_apply"
)
MOCK_HANDLE_NEW_TARGET_FILE = "zoltraak.converter.base_converter.BaseConverter.handle_new_target_file"
MOCK_UPDATE_TARGET_FILE_FROM_SOURCE_DIFF = (
    "zoltraak.converter.base_converter.BaseConverter.update_target_file_from_source_diff"
)

PROMPT_KEYWORD = "<<追加指示>>"


class TestBaseConverter(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.set_up_files()
        self.magic_info = MagicInfo()
        self.magic_info.file_info.update_source_target("pre.md", "output.md")
        self.magic_info.update()
        self.base_converter = BaseConverter(self.magic_info)
        self.set_mock_return_value(MOCK_HANDLE_EXISTING_TARGET_FILE)
        self.set_mock_return_value(MOCK_UPDATE_TARGET_FILE_PROPOSE_AND_APPLY)
        self.set_mock_return_value(MOCK_HANDLE_NEW_TARGET_FILE)
        self.set_mock_return_value(MOCK_UPDATE_TARGET_FILE_FROM_SOURCE_DIFF)

    def set_up_files(self):
        # テスト全体で使用するファイルのセットアップ
        os.makedirs("./past/source", exist_ok=True)
        with open("./past/source/pre.md", "w", encoding="utf-8") as f:
            f.write("# Test File\n\nThis is a test file." * 100)

        with open("./pre.md", "w", encoding="utf-8") as f:
            f.write("# Test File\n\nThis is a test file." * 100)

        with open("./output.md", "w", encoding="utf-8") as f:
            f.write("# Test File\n\nThis is a test file." * 100)

    def tearDown(self):
        super().tearDown()
        print("tearDown")

    # =============  test_convert_one_source  ==============
    # source: True, target: True
    # -> handle_existing_target_file()が呼ばれる
    def test_convert_one_source_true_target_true(self):
        result = self.base_converter.convert_one()
        self.assertEqual(result, "")
        self.check_mock_call_count(MOCK_HANDLE_EXISTING_TARGET_FILE, 1)
        self.check_mock_call_count(MOCK_HANDLE_NEW_TARGET_FILE, 0)
        self.assertIn(PROMPT_KEYWORD, self.base_converter.magic_info.prompt)

    # source: False, target: True
    def test_convert_one_source_false_target_true(self):
        os.remove("./pre.md")  # source ファイルを削除
        result = self.base_converter.convert_one()
        self.assertEqual(result, "")
        self.check_mock_call_count(MOCK_HANDLE_EXISTING_TARGET_FILE, 1)
        self.check_mock_call_count(MOCK_HANDLE_NEW_TARGET_FILE, 0)
        self.assertNotIn(PROMPT_KEYWORD, self.base_converter.magic_info.prompt)

    # source: True, target: False
    def test_convert_one_source_true_target_false(self):
        os.remove("./output.md")  # target ファイルを削除
        result = self.base_converter.convert_one()
        self.assertEqual(result, "")
        self.check_mock_call_count(MOCK_HANDLE_EXISTING_TARGET_FILE, 0)
        self.check_mock_call_count(MOCK_HANDLE_NEW_TARGET_FILE, 1)
        self.assertIn(PROMPT_KEYWORD, self.base_converter.magic_info.prompt)

    # source: False, target: False
    def test_convert_one_source_false_target_false(self):
        os.remove("./pre.md")  # source ファイルを削除
        os.remove("./output.md")  # target ファイルを削除
        result = self.base_converter.convert_one()
        self.assertEqual(result, "")
        self.check_mock_call_count(MOCK_HANDLE_EXISTING_TARGET_FILE, 0)
        self.check_mock_call_count(MOCK_HANDLE_NEW_TARGET_FILE, 1)
        self.assertNotIn(PROMPT_KEYWORD, self.base_converter.magic_info.prompt)

    # =============  handle_existing_target_file  ==============

    # is_source_changed: True, past_source: True
    def test_handle_existing_target_file_source_true_past_true(self):
        result = self.base_converter.handle_existing_target_file()
        self.assertEqual(result, "")
        self.check_mock_call_count(MOCK_UPDATE_TARGET_FILE_FROM_SOURCE_DIFF, 0)
        self.check_mock_call_count(MOCK_UPDATE_TARGET_FILE_PROPOSE_AND_APPLY, 0)
        self.assertNotIn(PROMPT_KEYWORD, self.base_converter.magic_info.prompt)
