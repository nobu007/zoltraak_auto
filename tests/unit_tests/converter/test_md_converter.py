import unittest
from unittest.mock import patch

from tests.unit_tests.converter.test_base_converter import TestBaseConverter
from zoltraak.converter.md_converter import MarkdownToMarkdownConverter
from zoltraak.schema.schema import FileInfo, MagicLayer, MagicMode
from zoltraak.utils.file_util import FileUtil

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
ALL_MOCK_HANDLE_NEW_TARGET_FILE = "zoltraak.converter.base_converter.BaseConverter.handle_new_target_file"
ALL_MOCK_UPDATE_TARGET_FILE_FROM_SOURCE_DIFF = (
    "zoltraak.converter.base_converter.BaseConverter.update_target_file_from_source_diff"
)

# キーワード定義
PROMPT_KEYWORD = "zoltraakシステムは曖昧なユーザー入力を"


class TestMarkdownToMarkdownConverter(TestBaseConverter):
    def setUp(self):
        super().setUp()

        self.magic_info.magic_layer = MagicLayer.LAYER_1_REQUEST_GEN
        self.magic_info.magic_mode = MagicMode.PROMPT_ONLY
        self.magic_info.file_info = FileInfo(
            prompt_file_path="prompt.md",
            pre_md_file_path="pre.md",
            md_file_path="output.md",
            py_file_path="script.py",
        )
        self.magic_info.file_info.update_source_target("pre.md", "output.md")
        self.magic_info.update()
        self.md_converter = MarkdownToMarkdownConverter(self.magic_info)

    def tearDown(self):
        super().tearDown()
        print("tearDown")

    def test_update_grimoire_and_prompt(self):
        self.md_converter.update_grimoire_and_prompt()
        self.assertIn(PROMPT_KEYWORD, self.md_converter.magic_info.prompt)
        self.check_mock_call_count_llm_generate_response(0)

    def test_apply_diff_to_target_file(self):
        with (
            patch.object(FileUtil, "read_file", return_value="current content"),
            patch.object(FileUtil, "write_file", return_value="new_output.md"),
        ):
            result = self.md_converter.apply_diff_to_target_file("output.md", "dummy_diff")
            self.assertEqual(result, "new_output.md")
            self.check_mock_call_count_llm_generate_response(1)


if __name__ == "__main__":
    unittest.main()
