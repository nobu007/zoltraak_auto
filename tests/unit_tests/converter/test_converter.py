import os
import unittest
from unittest.mock import patch

from tests.unit_tests.converter.test_base_converter import TestBaseConverter
from zoltraak.converter.converter import MarkdownToPythonConverter
from zoltraak.core.magic_workflow import MagicWorkflow
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
MOCK_GENERATE_TARGET_CODE = "zoltraak.gencode.TargetCodeGenerator.generate_target_code"
PROMPT_KEYWORD = "zoltraakシステムは曖昧なユーザー入力を"

# キーワード定義
PROMPT_KEYWORD = "zoltraakシステムは曖昧なユーザー入力を"
DUMMY_CONTENTS_PAST = "# Test File\nThis is a test file.\n# HASH: e32c2339" * 2
DUMMY_CONTENTS = "# Test File\nThis is a test file.\n# HASH: e32c2339" * 3


class TestMarkdownToPythonConverter(TestBaseConverter):
    def setUp(self):
        super().setUp()

        self.set_up_files()
        self.magic_workflow = MagicWorkflow()
        self.magic_info = self.magic_workflow.magic_info
        self.magic_info.magic_layer = MagicLayer.LAYER_5_CODE_GEN
        self.magic_info.magic_mode = MagicMode.PROMPT_ONLY
        self.magic_info.file_info = FileInfo(
            prompt_file_path="prompt.md",
            request_md_file_path="request.md",
            structure_file_path="structure.md",
            md_file_path="output.md",
            py_file_path="script.py",
        )
        self.magic_info.file_info.update_source_target("pre.md", "output.md")
        self.magic_info.update()
        self.prompt_manager = self.magic_workflow.prompt_manager
        self.converter = MarkdownToPythonConverter(self.magic_info, self.prompt_manager)

    def set_up_files(self):
        # テスト全体で使用するファイルのセットアップ
        os.makedirs("./past/source", exist_ok=True)
        with open("./past/source/pre.md", "w", encoding="utf-8") as f:
            f.write("past/source/pre.md\n" + DUMMY_CONTENTS_PAST)

        with open("./pre.md", "w", encoding="utf-8") as f:
            f.write("pre.md\n" + DUMMY_CONTENTS)

        with open("./output.md", "w", encoding="utf-8") as f:
            f.write("output.md\n" + DUMMY_CONTENTS)

    def tearDown(self):
        super().tearDown()
        print("tearDown")

    def test_update_grimoire_and_prompt(self):
        self.magic_workflow.update_grimoire_and_prompt(self.magic_info)
        self.assertIn("", self.magic_info.grimoire_compiler)
        self.assertIn(PROMPT_KEYWORD, self.converter.magic_info.prompt_input)
        self.check_mock_call_count_llm_generate_response(0)

    # 対象外： TestBaseConverterでmockに置き換えている（かつpy独自処理がない）
    # def test_handle_existing_target_file(self):
    #     result = self.converter.handle_existing_target_file()
    #     self.assertIn("output.md", result)
    #     self.check_mock_call_count_llm_generate_response(2)

    def test_handle_new_target_file(self):
        self.magic_info.prompt_input = ""
        result = self.converter.handle_new_target_file()
        self.assertEqual(result, os.path.abspath("output.md"))
        self.check_mock_call_count_llm_generate_response(1)

    def test_apply_diff_to_target_file(self):
        with (
            patch.object(FileUtil, "read_file", return_value="current content"),
            patch.object(FileUtil, "write_file", return_value="new_output.md"),
        ):
            result = self.converter.apply_diff_to_target_file("output.md", "dummy_diff")
            self.assertEqual(result, "new_output.md")
            self.check_mock_call_count_llm_generate_response(1)


if __name__ == "__main__":
    unittest.main()
