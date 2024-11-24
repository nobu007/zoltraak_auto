from deepeval.metrics import AnswerRelevancyMetric
from deepeval.models import DeepEvalBaseLLM
from deepeval.test_case import (
    LLMTestCase,
)
from pydantic import BaseModel

import zoltraak.llms.litellm_api as litellm
import zoltraak.settings


class SchemaStatements(BaseModel):
    statements: str


class CustomLitellmDeepEval(DeepEvalBaseLLM):
    def __init__(self):
        super().__init__()
        self.model_name = zoltraak.settings.model_name
        self.gemini_api_keys = zoltraak.settings.gemini_api_keys
        self.gemini_api_key = self.gemini_api_keys.split(",")[0]

    def load_model(self, *args, **kwargs):
        """dummy"""

    def generate(self, prompt: str, schema: BaseModel = SchemaStatements) -> str:  # noqa: W0221
        resp = litellm.generate_response_raw(
            model=self.model_name,
            prompt=prompt,
            api_key=self.gemini_api_key,
            response_format=schema,
        )
        if schema and hasattr(schema, "model_validate_json") and callable(schema.model_validate_json):
            return schema.model_validate_json(resp)
        return resp

    async def a_generate(self, prompt: str, schema: BaseModel = SchemaStatements) -> str:  # noqa: W0221
        return self.generate(prompt, schema)

    def get_model_name(self) -> str:  # noqa: W0221
        return self.model_name


class CustomAnswerRelevancyMetric(AnswerRelevancyMetric):
    def __init__(
        self,
        threshold: float = 0.5,
        model: CustomLitellmDeepEval = None,
        include_reason: bool = True,  # noqa: FBT001
        async_mode: bool = True,  # noqa: FBT001
        strict_mode: bool = False,  # noqa: FBT001
        verbose_mode: bool = False,  # noqa: FBT001
    ):
        super().__init__(
            threshold=threshold,
            model=model,
            include_reason=include_reason,
            async_mode=async_mode,
            strict_mode=strict_mode,
            verbose_mode=verbose_mode,
        )
        if self.model is None:
            self.model = CustomLitellmDeepEval()
        self.using_native_model = False


def get_score(src_content: str, dst_content: str, relation="input vs output") -> float:
    deep_eval = CustomLitellmDeepEval()
    eval_input = f"""Please judge src_contents vs dst_content(=output).
The relation of src_content and dst_content is "{relation}".

src_content:
{src_content}
"""
    test_case = LLMTestCase(input=eval_input, actual_output=dst_content)
    metric = AnswerRelevancyMetric(model=deep_eval)
    ret = metric.measure(test_case)
    print("ret=", ret)
    if ret is None:
        if "The score is" in metric.reason:
            score_str = metric.reason.split("The score is")[1].strip()  # "The score is"以降の文字列を取得
            score_str = score_str.split(" ")[0]  # Get the string up to the space
            score_str = "".join(filter(lambda c: c.isdigit() or c in ".-", score_str))
            ret = float(score_str)
            print("get score from metric.reason=", metric.reason)
            return ret
        ret = -1.0
    return ret


if __name__ == "__main__":

    class TestScore(BaseModel):
        score: float

    deep_eval = CustomLitellmDeepEval()
    test_case = LLMTestCase(input="今日の晩御飯を提案して", actual_output="カレー", expected_output="カレーライス")
    metric = AnswerRelevancyMetric(model=deep_eval)
    ret = metric.measure(test_case)
    print("ret=", ret)
