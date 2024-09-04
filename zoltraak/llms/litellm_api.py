import litellm
from litellm.integrations.custom_logger import CustomLogger
from collections import defaultdict


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


# デバッグ用
litellm.set_verbose = True

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
    fallbacks = ["claude-3-5-sonnet-20240620"]
    response = litellm.completion(
        model=model,
        messages=[{"content": prompt, "role": "user"}],
        max_tokens=max_tokens,
        temperature=temperature,
        fallbacks=fallbacks,
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
