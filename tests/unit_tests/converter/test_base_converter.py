import os

from tests.unit_tests.helper import TestCaseBase
from zoltraak.converter.base_converter import BaseConverter
from zoltraak.schema.schema import MagicInfo


class TestBaseConverter(TestCaseBase):
    def setUp(self):
        super().setUp()

        self.magic_info = MagicInfo()
        self.magic_info.file_info.update_source_target("pre.md", "output.md")
        self.magic_info.update()
        self.converter = BaseConverter(self.magic_info)
        self.set_up_files()

    def set_up_files(self):
        # テスト全体で使用するファイルのセットアップ
        os.makedirs("./past/source", exist_ok=True)
        with open("./past/source/pre.md", "w", encoding="utf-8") as f:
            f.write("# Test File\n\nThis is a test file.")

        with open("./pre.md", "w", encoding="utf-8") as f:
            f.write("# Test File\n\nThis is a test file.")

        with open("./output.md", "w", encoding="utf-8") as f:
            f.write("# Test File\n\nThis is a test file.")

    def tearDown(self):
        super().tearDown()
        print("tearDown")

    # source: True, target: True
    def test_convert_one_source_true_target_true(self):
        result = self.converter.convert_one()
        self.assertEqual(result, "output.md")
        self.check_mock_call_count_llm_generate_response(2)

    # source: False, target: True
    def test_convert_one_source_false_target_true(self):
        os.remove("./pre.md")
        result = self.converter.convert_one()
        self.assertEqual(result, "output.md")
        self.check_mock_call_count_llm_generate_response(2)

    # source: True, target: False
    def test_convert_one_source_true_target_false(self):
        os.remove("./output.md")
        result = self.converter.convert_one()
        self.assertEqual(result, "requirements/output.md")
        self.check_mock_call_count_llm_generate_response(1)

    # source: False, target: False
    def test_convert_one_source_false_target_false(self):
        os.remove("./pre.md")
        os.remove("./output.md")
        result = self.converter.convert_one()
        self.assertEqual(result, "requirements/output.md")
        self.check_mock_call_count_llm_generate_response(1)
