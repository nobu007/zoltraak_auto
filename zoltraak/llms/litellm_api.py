import os
from collections import defaultdict

import litellm
from litellm import Router
from litellm.integrations.custom_logger import CustomLogger


class ModelStatsLogger(CustomLogger):
    def __init__(self):
        self.stats = defaultdict(lambda: {"count": 0, "total_tokens": 0})

    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        model = kwargs["model"]
        if response_obj:
            tokens = response_obj["usage"]["total_tokens"]
            self.stats[model]["count"] += 1
            self.stats[model]["total_tokens"] += tokens

    def get_stats(self):
        return dict(self.stats)


# ロガーを設定
logger = ModelStatsLogger()
completion = litellm.completion
litellm.callbacks = [logger]


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
    DEFAULT_MODEL_GEMINI = "gemini/gemini-1.5-flash-latest"
    DEFAULT_MODEL_CLAUDE = "claude-3-5-sonnet-20240620"
    default_model_list = [
        {
            "model_name": "gemini_bkup1",
            "litellm_params": {
                "model": DEFAULT_MODEL_GEMINI,
                "api_key": os.getenv("GEMINI_API_KEY"),
            },
        },
        {
            "model_name": "gemini_bkup2",
            "litellm_params": {
                "model": DEFAULT_MODEL_GEMINI,
                "api_key": os.getenv("GEMINI_API_KEY2"),
            },
        },
        {
            "model_name": "claude_bkup",
            "litellm_params": {
                "model": DEFAULT_MODEL_CLAUDE,
                "api_key": os.getenv("ANTHROPIC_API_KEY"),
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

    router = Router(model_list=model_list, fallbacks=fallbacks_dict)
    response = router.completion(
        model=model,
        messages=[{"content": prompt, "role": "user"}],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()


def show_used_total_tokens():
    # 統計を取得して表示
    stats = logger.get_stats()
    for model, data in stats.items():
        print(f"Model: {model}")
        print(f"  Total requests: {data['count']}")
        print(f"  Total tokens: {data['total_tokens']}")
        print(f"  Average tokens per request: {data['total_tokens'] / data['count']:.2f}")


if __name__ == "__main__":
    model = "claude-3-haiku-20240307"
    prompt = "今日の晩御飯を提案して"
    max_tokens = 100
    temperature = 0.8

    response = generate_response(model, prompt, max_tokens, temperature)

    print(response)
