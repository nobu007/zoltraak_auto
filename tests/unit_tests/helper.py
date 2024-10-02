import unittest
from typing import Any
from unittest.mock import MagicMock, patch


class MockManager:
    def __init__(self, mode: str = "read"):
        self.mode = mode
        self.mock_dict: dict[str, MagicMock] = {}
        self._init_default_mocks()

    def _init_default_mocks(self):
        # FileUtilを無効化するfixtureを生成
        # self._add_mock("fixture_file_util_read_ok", "zoltraak.utils.file_util.FileUtil.read_file", "ok")
        # self._add_mock("fixture_file_util_read_long", "zoltraak.utils.file_util.FileUtil.read_file", "ok")
        self._add_mock("fixture_file_util_write_ok", "zoltraak.utils.file_util.FileUtil.write_file", "ok")
        self._add_mock("fixture_file_util_write_ng", "zoltraak.utils.file_util.FileUtil.write_file", "ok")

        # llm呼び出しを無効化するfixtureを生成
        self._add_mock("fixture_litellm_api_generate_response_ok", "zoltraak.llms.litellm_api.generate_response", "ok")

    def _add_mock(self, mock_name: str, mock_target: str, return_value: Any):
        # FileUtilを無効化するfixtureを生成
        self.mock_dict[mock_name] = self.parameterized_mock_factory(mock_target, return_value)

    def get_mock_call_count(self, mock_name: str):
        # モック呼び出しの回数を取得
        return self.mock_dict[mock_name].call_count

    def set_mock_return_value(self, mock_target: str = "", return_value: Any = 0, mock_alias: str = "") -> None:
        # リターン値を書き換えるモックを設定
        mock_name = mock_alias if mock_alias else mock_target
        if mock_name and mock_target not in self.mock_dict:
            self._add_mock(mock_name, mock_target, return_value)

        self.mock_dict[mock_name].return_value = return_value

    def set_mock_side_effect(
        self, mock_target: str = "", side_effect: Any = lambda: None, mock_alias: str = ""
    ) -> None:
        # サイドエフェクトを持つモックを設定
        mock_name = mock_alias if mock_alias else mock_target
        if mock_name and mock_target not in self.mock_dict:
            self._add_mock(mock_name, mock_target, 0)
        self.mock_dict[mock_name].side_effect = side_effect

    def parameterized_mock_factory(self, mock_target: str, return_value: Any):
        # モックを生成
        instance = MagicMock()
        instance.return_value = return_value
        patch(mock_target, instance).start()
        return instance


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        # llm呼び出しを無効化するmockをセットアップ
        self.mock_manager = MockManager()

    def tearDown(self):
        # モックを停止
        patch.stopall()

    def check_mock_call_count(self, mock_name: str, expected_count: int):
        # モック呼び出しの回数をチェック
        self.assertEqual(self.mock_manager.get_mock_call_count(mock_name), expected_count, mock_name)

    def check_mock_call_count_llm_generate_response(self, expected_count: int):
        # llm呼び出しの回数をチェック(特殊処理)
        mock_name = "fixture_litellm_api_generate_response_ok"
        self.assertEqual(self.mock_manager.get_mock_call_count(mock_name), expected_count, mock_name)

    def set_mock_return_value(self, mock_name: str, mock_target: str = "", return_value: Any = 0):
        # リターン値を書き換えるモックを設定
        self.mock_manager.set_mock_return_value(mock_name, mock_target, return_value)

    def set_mock_side_effect(self, mock_name: str, mock_target: str = "", side_effect: Any = lambda: None):
        # サイドエフェクトを持つモックを設定
        self.mock_manager.set_mock_side_effect(mock_name, mock_target, side_effect)
