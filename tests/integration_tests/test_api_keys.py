import zoltraak.llms.litellm_api as litellm
import zoltraak.settings
from tests.unit_tests.helper import BaseTestCase


class TestZoltraakCommand(BaseTestCase):  # TestZoltraakCommand クラスを定義し、 BaseTestCaseを継承します。
    def test_api_keys_gemini(self):
        """
        api_keysのテスト
        """
        model_name = zoltraak.settings.model_name
        gemini_api_keys = zoltraak.settings.gemini_api_keys
        prompt = "今日の晩御飯を提案して"
        max_tokens = 100
        temperature = 0.8

        for i, gemini_api_key in enumerate(gemini_api_keys.split(",")):
            print("i=", i)
            response = litellm.generate_response_raw(
                model=model_name, prompt=prompt, max_tokens=max_tokens, temperature=temperature, api_key=gemini_api_key
            )

            # レスポンスが文字列であることを確認
            self.assertTrue(isinstance(response, str))

            # レスポンスが空でないことを確認
            self.assertNotEqual(response.strip(), "")
