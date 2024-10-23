import os
from collections import defaultdict
from typing import ClassVar

import anyio
import litellm
from litellm import ModelResponse, Router
from litellm.integrations.custom_logger import CustomLogger

from zoltraak.utils.file_util import FileUtil
from zoltraak.utils.log_util import log, log_w


class ModelStatsLogger(CustomLogger):
    def __init__(self):
        self.stats = defaultdict(lambda: {"count": 0, "total_tokens": 0, "start_time": None, "end_time": None})

    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        log_w("log_success_event start_time=%s, end_time=%s", start_time, end_time)
        model = kwargs["model"]
        if response_obj and "usage" in response_obj:
            tokens = response_obj["usage"].get("total_tokens", 0)
            self.stats[model]["count"] += 1
            self.stats[model]["total_tokens"] += tokens
            if self.stats[model]["start_time"] is None:
                self.stats[model]["start_time"] = start_time
            self.stats[model]["end_time"] = end_time

    def get_stats(self) -> dict:
        return dict(self.stats)


# ロガーを設定(ファイル内グローバル変数)
logger_ = ModelStatsLogger()
litellm.callbacks = [logger_]


DEFAULT_MODEL_GEMINI = "gemini/gemini-1.5-flash-latest"
DEFAULT_MODEL_CLAUDE = "claude-3-5-sonnet-20240620"

# https://ai.google.dev/gemini-api/docs/models/gemini?hl=ja
RPM_GEMINI_FLASH = 100  # 1分あたりのリクエスト数(MAX: 1500)
RPM_GEMINI_PRO = 2  # 1分あたりのリクエスト数(MAX: 1500)
RPM_ANTHROPIC_CLAUDE = 1  # 1分あたりのリクエスト数
RPM_OTHER = 1  # 1分あたりのリクエスト数

TPM_GEMINI_FLASH = 200000  # 1分あたりのトークン数(MAX: 100万)
TPM_GEMINI_PRO = 10000  # 1分あたりのトークン数(MAX: 32,000)
TPM_ANTHROPIC_CLAUDE = 100000  # 1分あたりのトークン数(MAX: ？？)


def generate_response(
    model: str,
    prompt: str,
    max_tokens: int = 4000,
    temperature: float = 0.0,
    *,
    is_async: bool = False,
) -> str:
    return anyio.run(
        generate_response_async,
        model,
        prompt,
        max_tokens,
        temperature,
        is_async,
    )


async def generate_response_async(
    model: str,
    prompt: str,
    max_tokens: int = 4000,
    temperature: float = 0.0,
    is_async: bool = False,  # noqa: FBT001
) -> str:
    api = LitellmApi()
    return await api.generate_response(model, prompt, max_tokens, temperature, is_async=is_async)


def show_used_total_tokens():
    return LitellmApi().show_stats()


class LitellmApi:
    """LitellmApi 設計メモ(with anyio)

    # 非同期処理の実装ポイント
    非同期の実装ポイントを使用する際に理解すべきポイントを以下に整理します。

    ## 非同期⇒非同期
    非同期関数同士の呼び出しでは、awaitを必ず使います。
    await 関数() の形で呼び出すことで、非同期関数が実行されます。

    ## 非同期⇒同期
    非同期関数から同期関数を呼び出すには、anyio.to_thread.run_sync()を使用します。
    これにより、ブロッキングな同期関数を別スレッドで実行できます。

    ## 同期⇒非同期
    同期関数から非同期関数を実行する際には、anyio.run()を使用します。
    これにより、同期コードの中で非同期関数を簡単に実行できます。

    ## 間違わないための理解ポイント：
    awaitは非同期関数内で使う必要がある。非同期関数を呼び出すときは、awaitを忘れない。
    同期と非同期を正しく橋渡しするために、anyioのrun系関数（anyio.runやto_thread.run_sync）を使う。
    """

    # Model constants
    DEFAULT_MODEL_GEMINI = "gemini/gemini-1.5-flash-latest"
    DEFAULT_MODEL_CLAUDE = "claude-3-5-sonnet-20240620"

    # Rate limits
    RPM_LIMITS: ClassVar[dict[str, int]] = {"gemini_flash": 100, "gemini_pro": 2, "anthropic_claude": 1, "other": 1}

    def __init__(self, logger: ModelStatsLogger = logger_):
        self.logger = logger
        self._router: Router | None = None

    def _get_router(self, model: str) -> Router:
        """Initialize and return a router with proper configuration."""
        if self._router:
            return self._router

        api_key = self._get_api_key(model)
        model_list = self._create_model_list(model, api_key)
        fallbacks_dict = self._create_fallbacks_dict()

        self._router = Router(model_list=model_list, fallbacks=fallbacks_dict, retry_after=3)
        return self._router

    def _get_api_key(self, model: str) -> str:
        """Get appropriate API key based on model type."""
        key_mapping = {"claude": "ANTHROPIC_API_KEY", "groq": "GROQ_API_KEY", "gemini": "GEMINI_API_KEY"}

        for model_type, env_var in key_mapping.items():
            if model_type in model:
                return os.getenv(env_var, "")
        return os.getenv("GEMINI_API_KEY", "")  # default fallback

    def _create_model_list(self, primary_model: str, api_key: str) -> list[dict]:
        """Create model list configuration including fallbacks."""
        base_model = {
            "model_name": "main",
            "litellm_params": {
                "model": primary_model,
                "api_key": api_key,
                "rpm": self.RPM_LIMITS["other"],
            },
        }

        fallback_models = [
            {
                "model_name": "gemini_bkup1",
                "litellm_params": {
                    "model": self.DEFAULT_MODEL_GEMINI,
                    "api_key": os.getenv("GEMINI_API_KEY"),
                    "num_retries": 2,
                    "rpm": self.RPM_LIMITS["gemini_flash"],
                },
            },
            {
                "model_name": "gemini_bkup2",
                "litellm_params": {
                    "model": self.DEFAULT_MODEL_GEMINI,
                    "api_key": os.getenv("GEMINI_API_KEY2"),
                    "num_retries": 2,
                    "rpm": self.RPM_LIMITS["gemini_flash"],
                },
            },
            {
                "model_name": "claude_bkup",
                "litellm_params": {
                    "model": self.DEFAULT_MODEL_CLAUDE,
                    "api_key": os.getenv("ANTHROPIC_API_KEY"),
                    "num_retries": 2,
                    "rpm": self.RPM_LIMITS["anthropic_claude"],
                },
            },
        ]

        # 全モデルを配列に入れて返す
        return [base_model, *fallback_models]

    @staticmethod
    def _create_fallbacks_dict() -> list[dict]:
        """Create fallback configuration."""
        return [
            {"main": ["gemini_bkup1", "gemini_bkup2"]},
            {"gemini_bkup1": ["claude_bkup"]},
            {"gemini_bkup2": ["claude_bkup"]},
        ]

    async def generate_response(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 4000,
        temperature: float = 0.0,
        *,
        is_async: bool = False,
    ) -> str:
        """同期と非同期を共通の関数で呼べるようにした"""
        if not self._validate_input(prompt, max_tokens):
            return ""

        if is_async:
            # Async call
            return await self._generate_async(model, prompt, max_tokens, temperature)
        # Sync call
        return await anyio.to_thread.run_sync(
            self._generate_sync, model, prompt, max_tokens, temperature
        )  # 別スレッドで同期関数を実行

    def _validate_input(self, prompt: str, max_tokens: int) -> bool:
        """Validate input parameters."""
        if not prompt.strip():
            log_w("Empty prompt received")
            return False

        prompt_length = len(prompt)
        if prompt_length + 1000 > max_tokens:
            log_w("WARN: max_tokens might be too small. prompt len=%s, max_tokens=%d", prompt_length, max_tokens)
            FileUtil.write_file(f"over_prompt_{prompt_length}.txt", prompt)

        return True

    async def _generate_async(self, model: str, prompt: str, max_tokens: int, temperature: float) -> str:
        """Handle async response generation."""
        router = self._get_router(model)
        response = await router.acompletion(
            model=model,
            messages=[{"content": prompt, "role": "user"}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return self._process_response(response, prompt)

    def _generate_sync(self, model: str, prompt: str, max_tokens: int, temperature: float) -> str:
        """Handle sync response generation."""
        router = self._get_router(model)
        response = router.completion(
            model=model,
            messages=[{"content": prompt, "role": "user"}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return self._process_response(response, prompt)

    def _process_response(self, response: ModelResponse, prompt: str) -> str:
        """Process and validate response."""
        if not response.choices or not response.choices[0].message:
            log_w("Invalid response received for prompt: %s", prompt)
            return ""
        return response.choices[0].message.content.strip()

    def show_stats(self) -> None:
        """Display usage statistics."""
        stats = self.logger.get_stats()
        for model, data in stats.items():
            if data["count"] > 0:
                avg_tokens = data["total_tokens"] / data["count"]
                log(f"Model: {model}")
                log(f"  Total requests: {data['count']}")
                log(f"  Total tokens: {data['total_tokens']}")
                log(f"  Average tokens per request: {avg_tokens:.2f}")


if __name__ == "__main__":

    async def main():
        model_ = "claude-3-haiku-20240307"
        prompt_ = "今日の晩御飯を提案して"
        max_tokens_ = 100
        temperature_ = 0.8

        llm = LitellmApi()
        response_ = await generate_response_async(model_, prompt_, max_tokens_, temperature_, is_async=True)
        print(response_)
        llm.show_stats()

    anyio.run(main)
