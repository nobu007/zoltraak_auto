import os
from collections import defaultdict

import litellm
from litellm import ModelResponse, Router
from litellm.integrations.custom_logger import CustomLogger

from zoltraak.utils.log_util import log, log_w


class ModelStatsLogger(CustomLogger):
    def __init__(self):
        self.stats = defaultdict(lambda: {"count": 0, "total_tokens": 0, "start_time": None, "end_time": None})

    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        log_w("log_success_event start_time=%s, end_time=%s", start_time, end_time)
        model = kwargs["model"]
        if response_obj:
            tokens = response_obj["usage"]["total_tokens"]
            self.stats[model]["count"] += 1
            self.stats[model]["total_tokens"] += tokens
            if self.stats[model]["start_time"] is None:
                self.stats[model]["start_time"] = start_time
            self.stats[model]["end_time"] = end_time

    def get_stats(self):
        return dict(self.stats)


# ロガーを設定
logger = ModelStatsLogger()
litellm.callbacks = [logger]


DEFAULT_MODEL_GEMINI = "gemini/gemini-1.5-flash-latest"
DEFAULT_MODEL_CLAUDE = "claude-3-5-sonnet-20240620"


def generate_response(model, prompt, max_tokens, temperature):
    """
    LiteLLM APIを使用してプロンプトに対する応答を生成する関数。

    Args:
        prompt (str): 応答を生成するためのプロンプト。
        max_tokens (int): 生成する最大トークン数。
        temperature (float): 生成時の温度パラメータ。

    Returns:
        str: 生成された応答テキスト。
    """
    # エラー時のリトライ定義
    fallbacks_dict = [
        {"main": ["gemini_bkup1", "gemini_bkup2"]},
        {"gemini_bkup1": ["claude_bkup"]},
        {"gemini_bkup2": ["claude_bkup"]},
    ]
    default_model_list = [
        {
            "model_name": "gemini_bkup1",
            "litellm_params": {
                "model": DEFAULT_MODEL_GEMINI,
                "api_key": os.getenv("GEMINI_API_KEY"),
                "num_retries": 2,
            },
        },
        {
            "model_name": "gemini_bkup2",
            "litellm_params": {
                "model": DEFAULT_MODEL_GEMINI,
                "api_key": os.getenv("GEMINI_API_KEY2"),
                "num_retries": 2,
            },
        },
        {
            "model_name": "claude_bkup",
            "litellm_params": {
                "model": DEFAULT_MODEL_CLAUDE,
                "api_key": os.getenv("ANTHROPIC_API_KEY"),
                "num_retries": 2,
            },
        },
    ]

    # modelに応じたapi_keyを準備
    api_key_env = "GEMINI_API_KEY"
    if "claude" in model:
        api_key_env = "ANTHROPIC_API_KEY"
    if "groq" in model:
        api_key_env = "GROQ_API_KEY"
    api_key = os.getenv(api_key_env)

    model_list = [
        {
            "model_name": "main",
            "litellm_params": {
                "model": model,
                "api_key": api_key,
            },
        },
        *default_model_list,  # 配列を展開して追加
    ]

    if not show_input_prompt_warning(prompt):
        return "promptが空なので応答を生成できませんでした"
    router = Router(model_list=model_list, fallbacks=fallbacks_dict, retry_after=3)  # 3秒待機してからリトライ
    log("prompt len=%s, max_tokens=%d", len(prompt), max_tokens)
    if len(prompt) + 1000 > max_tokens:
        log_w("WARN: max_tokens might is too small. prompt len=%s, max_tokens=%d", len(prompt), max_tokens)
    response = router.completion(
        model=model,
        messages=[{"content": prompt, "role": "user"}],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    if not show_response_warning(response, prompt):
        # 差分を生成する処理で差分なしの時は空白なので、空白を返す
        return ""
    return response.choices[0].message.content.strip()


def show_input_prompt_warning(prompt: str) -> bool:
    # 異常なpromptが来たらログで警告する
    if prompt.strip() == "":
        log_w("Empty prompt received")
        return False
    return True


def show_response_warning(response: ModelResponse, prompt: str) -> bool:
    # 異常なresponseが来たらログで警告する
    if len(response.choices) == 0:
        log_w("Empty response.choices received. prompt=%s", prompt)
        return False
    if not response.choices[0].message:
        log_w("Empty message received. message=%s. prompt=%s", str(response.choices[0].message), prompt)
        return False
    if not response.choices[0].message.content:
        log_w("Invalid content=%s. prompt=%s", str(response.choices[0].message.content), prompt)
        return False
    return True


def show_used_total_tokens():
    # 統計を取得して表示
    stats = logger.get_stats()
    for model, data in stats.items():
        log(f"Model: {model}")
        log(f"  Total requests: {data['count']}")
        log(f"  Total tokens: {data['total_tokens']}")
        log(f"  Average tokens per request: {data['total_tokens'] / data['count']:.2f}")


if __name__ == "__main__":
    model_ = "claude-3-haiku-20240307"
    prompt = "今日の晩御飯を提案して"
    max_tokens = 100
    temperature = 0.8

    response_ = generate_response(model_, prompt, max_tokens, temperature)

    print(response_)
