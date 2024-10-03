import inspect
import unittest
import unittest.mock
from typing import Any
from unittest.mock import MagicMock, patch


class MockManager:
    """複数のモックをmock_nameという名前でアクセスできるようにするクラス"""

    def __init__(self, mode: str = "read"):
        self.mode = mode
        self.mock_dict: dict[str, MagicMock] = {}
        self._init_default_mocks()

    def _init_default_mocks(self):
        # FileUtilを無効化するfixtureを生成
        # self._set_mock("fixture_file_util_read_ok", "zoltraak.utils.file_util.FileUtil.read_file", "ok")
        # self._set_mock("fixture_file_util_read_long", "zoltraak.utils.file_util.FileUtil.read_file", "ok")
        self._set_mock("fixture_file_util_write_ok", "zoltraak.utils.file_util.FileUtil.write_file", return_value="ok")
        self._set_mock("fixture_file_util_write_ng", "zoltraak.utils.file_util.FileUtil.write_file", return_value="ok")

        # llm呼び出しを無効化するfixtureを生成
        self._set_mock("fixture_litellm_api_generate_response_ok", "zoltraak.llms.litellm_api.generate_response", "ok")

    def _set_mock(self, mock_name: str, mock_target: str, return_value: Any = ""):
        # モックを生成してreturn_valueを設定
        self.mock_dict[mock_name] = self._parameterized_mock_factory(mock_target, return_value)
        print(f"set_mock= name: {mock_name}, target: {mock_target}, return_value: {return_value}")
        # print(f"  mock_dict[{mock_name}] = {self._get_mock_name(self.mock_dict[mock_name])}")

    def _parameterized_mock_factory(self, mock_target: str, return_value: Any):
        # モックを生成
        instance = MagicMock()
        instance.return_value = return_value
        patcher = patch(mock_target, instance)
        return patcher.start()

    def _add_cleanup(self, cleanup_func):
        if not hasattr(self, "_cleanups"):
            self._cleanups = []
        self._cleanups.append(cleanup_func)

    def cleanup(self):
        if hasattr(self, "_cleanups"):
            for cleanup_func in self._cleanups:
                cleanup_func()

    def _get_mock(self, mock_name: str) -> None | MagicMock:
        # モックを取得
        if mock_name in self.mock_dict:
            return self.mock_dict[mock_name]
        return None

    # def _get_mock_name(self, mock):
    #     """モックオブジェクトの名前を取得する改良版関数"""
    #     # まず、_mock_new_nameをチェック
    #     if mock._mock_new_name:
    #         return mock._mock_new_name

    #     # 次に、specをチェック
    #     if mock._spec_class:
    #         return mock._spec_class.__name__
    #     if mock._spec:
    #         return mock._spec.__name__

    #     # parent._mock_childrenをチェック
    #     if mock._mock_parent is not None:
    #         for name, child in mock._mock_parent._mock_children.items():
    #             if child is mock:
    #                 return name

    #     # 最後に、__name__属性をチェック
    #     if hasattr(mock, "__name__"):
    #         return mock.__name__

    #     # 上記のどれも該当しない場合は、デフォルトの文字列表現を返す
    #     return str(mock)

    def get_mock_call_count(self, mock_name: str):
        # モック呼び出しの回数を取得
        return self._get_mock(mock_name).call_count

    def set_mock_return_value(self, mock_target: str = "", mock_alias: str = "", return_value: Any = "") -> None:
        # モックをmock_dictから取り出すときの名前
        mock_name = mock_alias if mock_alias else mock_target
        if not mock_name:
            return

        # リターン値を書き換えるモックを設定
        mock = self._get_mock(mock_name)
        if mock:
            # 既存のモックに値だけ設定
            mock.return_value = return_value
        else:
            # 新規のモックを作成
            self._set_mock(mock_name, mock_target, return_value)

    def set_mock_side_effect(
        self, mock_target: str = "", mock_alias: str = "", side_effect: Any = lambda: None
    ) -> None:
        # サイドエフェクトを持つモックを設定
        mock_name = mock_alias if mock_alias else mock_target
        if mock_name and mock_target not in self.mock_dict:
            self._set_mock(mock_name, mock_target, 0)
        self.mock_dict[mock_name].side_effect = side_effect

    @staticmethod
    def get_fully_qualified_name(obj: Any) -> str:
        module = inspect.getmodule(obj)
        if module is None or module.__name__ == "__main__":
            return obj.__qualname__
        return f"{module.__name__}.{obj.__qualname__}"


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

    def set_mock_return_value(self, mock_target: str = "", mock_alias: str = "", return_value: Any = ""):
        # リターン値を書き換えるモックを設定
        self.mock_manager.set_mock_return_value(
            mock_target=mock_target, mock_alias=mock_alias, return_value=return_value
        )

    def set_mock_side_effect(self, mock_target: str = "", mock_alias: str = "", side_effect: Any = lambda: None):
        # サイドエフェクトを持つモックを設定
        self.mock_manager.set_mock_side_effect(mock_target=mock_target, mock_alias=mock_alias, side_effect=side_effect)
