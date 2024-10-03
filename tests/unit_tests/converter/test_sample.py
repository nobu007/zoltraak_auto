import os

from tests.unit_tests.helper import BaseTestCase
from zoltraak.converter.base_converter import BaseConverter
from zoltraak.schema.schema import MagicInfo

# モック用の定義
# 1. モジュールのインポート方法に応じたモックの定義(bb.xxを置き換える例):
#    a. from import文を使用する場合:
#       例: cc.pyで「from aa import bb」としてbb.xxを使用する場合
#       MOCK_DEFINITION = "cc.bb.xx" <= "aa.bb.xx"ではない
#    b. import文を使用する場合:
#       例: aa.pyで「import bb」としてbb.xxを使用する場合
#       MOCK_DEFINITION = "aa.bb.xx"
MOCK_GENERATE_MD_FROM_PROMPT = "zoltraak.converter.base_converter.generate_md_from_prompt"

# キーワード定義
PROMPT_KEYWORD = "<<追加指示>>"
DUMMY_CONTENTS = "# Test File\nThis is a test file.\n# HASH: e32c2339" * 100


class TestBaseConverter(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.set_up_files()
        self.magic_info = MagicInfo()
        self.magic_info.file_info.update_source_target("pre.md", "output.md")
        self.magic_info.update()
        self.base_converter = BaseConverter(self.magic_info)

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

    # =============  handle_new_target_file  ==============

    def test_handle_new_target_file(self):
        self.set_mock_return_value(MOCK_GENERATE_MD_FROM_PROMPT, return_value=PROMPT_KEYWORD)
        result = self.base_converter.handle_new_target_file()
        self.assertEqual(result, PROMPT_KEYWORD)
        self.check_mock_call_count_llm_generate_response(0)
