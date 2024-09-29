import os
import unittest
from unittest.mock import MagicMock, patch

from zoltraak.md_converter import MarkdownToMarkdownConverter
from zoltraak.schema.schema import FileInfo, MagicInfo, MagicLayer, MagicMode
from zoltraak.utils.file_util import FileUtil

PROMPT_KEYWORD = "zoltraakシステムは曖昧なユーザー入力を"


class TestMarkdownToMarkdownConverter(unittest.TestCase):
    def setUp(self):
        self.magic_mock_generate_response = MagicMock()
        self.magic_mock_generate_response.return_value = "dummy"
        patch("zoltraak.llms.litellm_api.generate_response", self.magic_mock_generate_response).start()

        self.magic_info = MagicInfo(
            magic_layer=MagicLayer.LAYER_1_REQUEST_GEN,
            magic_mode=MagicMode.PROMPT_ONLY,
            file_info=FileInfo(
                prompt_file_path="prompt.md",
                pre_md_file_path="pre.md",
                md_file_path="output.md",
                py_file_path="script.py",
            ),
        )
        self.magic_info.file_info.update_source_target("pre.md", "output.md")
        self.magic_info.update()
        self.converter = MarkdownToMarkdownConverter(self.magic_info)
        self.set_up_files()

    def set_up_files(self):
        # テスト全体で使用するファイルのセットアップ
        os.makedirs("./past/source", exist_ok=True)
        with open("./past/source/pre.md", "w") as f:
            f.write("# Test File\n\nThis is a test file.")

        with open("./pre.md", "w") as f:
            f.write("# Test File\n\nThis is a test file.")

        with open("./output.md", "w") as f:
            f.write("# Test File\n\nThis is a test file.")

    def tearDown(self):
        patch.stopall()  # モックを停止

    def test_convert_one_first_time(self):
        os.remove("./output.md")
        result = self.converter.convert_one()
        self.assertEqual(result, "requirements/output.md")
        self.assertEqual(self.magic_mock_generate_response.call_count, 1)

    def test_convert_one_second_time(self):
        result = self.converter.convert_one()
        self.assertEqual(result, "output.md")
        self.assertEqual(self.magic_mock_generate_response.call_count, 2)

    def test_update_grimoire_and_prompt(self):
        self.converter.update_grimoire_and_prompt()
        self.assertIn(PROMPT_KEYWORD, self.converter.magic_info.prompt)
        self.assertEqual(self.magic_mock_generate_response.call_count, 0)

    def test_handle_existing_target_file(self):
        with patch("os.path.exists", return_value=True):
            result = self.converter.handle_existing_target_file()
            self.assertIn("output.md", result)
            self.assertEqual(self.magic_mock_generate_response.call_count, 2)

    def test_handle_new_target_file(self):
        with patch("zoltraak.gen_markdown.generate_md_from_prompt", return_value="output.md"):
            result = self.converter.handle_new_target_file()
            self.assertEqual(result, "requirements/output.md")
            self.assertEqual(self.magic_mock_generate_response.call_count, 1)

    def test_apply_diff_to_target_file(self):
        with (
            patch.object(FileUtil, "read_file", return_value="current content"),
            patch.object(FileUtil, "write_file", return_value="new_output.md"),
        ):
            result = self.converter.apply_diff_to_target_file("output.md", "dummy_diff")
            self.assertEqual(result, "new_output.md")
            self.assertEqual(self.magic_mock_generate_response.call_count, 1)


if __name__ == "__main__":
    unittest.main()
