import os
from collections import defaultdict
from contextlib import suppress
from typing import Any

import anyio
import litellm
from litellm import ModelResponse, Router
from litellm.integrations.custom_logger import CustomLogger

from zoltraak import settings
from zoltraak.utils.file_util import FileUtil
from zoltraak.utils.log_util import log, log_head, log_w

# デバッグ用
os.environ["LITELLM_LOG"] = "DEBUG"


class ModelStatsLogger(CustomLogger):
    def __init__(self):
        self.stats = defaultdict(lambda: {"count": 0, "total_tokens": 0, "start_time": None, "end_time": None})

    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        duration_time = end_time - start_time
        log_w("log_success_event duration_time=%s", duration_time)
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


# https://ai.google.dev/pricing#1_5flash
RPM_GEMINI_FLASH = 10  # 1分あたりのリクエスト数(MAX: 15)
RPM_GEMINI_PRO = 2  # 1分あたりのリクエスト数(MAX: 1500)
RPM_ANTHROPIC_CLAUDE = 5  # 1分あたりのリクエスト数
RPM_OTHER = 10  # 1分あたりのリクエスト数

TPM_GEMINI_FLASH = 300000  # 1分あたりのトークン数(MAX: 100万)
TPM_GEMINI_PRO = 10000  # 1分あたりのトークン数(MAX: 32,000)
TPM_ANTHROPIC_CLAUDE = 100000  # 1分あたりのトークン数(MAX: ??)
TPM_OTHER = 100000  # 1分あたりのトークン数

# Rate limits
RPM_LIMITS: dict = {
    "gemini_flash": RPM_GEMINI_FLASH,
    "gemini_pro": RPM_GEMINI_PRO,
    "anthropic_claude": RPM_ANTHROPIC_CLAUDE,
    "other": RPM_OTHER,
}
TPM_LIMITS: dict = {
    "gemini_flash": TPM_GEMINI_FLASH,
    "gemini_pro": TPM_GEMINI_PRO,
    "anthropic_claude": TPM_ANTHROPIC_CLAUDE,
    "other": TPM_OTHER,
}


def flexible_run(async_func: callable, *args, **kwargs) -> Any:
    """
    コンテキストに応じて適切な方法で非同期関数を実行する
    """
    try:
        with suppress(RuntimeError):
            # 現在のイベントループでのタスクを取得しようとする
            anyio.get_current_task()
            return anyio.from_thread.run(async_func, *args, **kwargs)

        # イベントループが存在しない場合は、新しいイベントループを作成して非同期関数を実行する
        return anyio.run(async_func, *args, **kwargs)
    except Exception as e:
        # エラーハンドリング
        print(f"Error executing async function: {e}")
        raise


def generate_response(
    model: str,
    prompt: str,
    max_tokens: int = 4000,
    temperature: float = 0.0,
    *,
    is_async: bool = False,
) -> str:
    return flexible_run(
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
    return await api.generate_response(
        model=model, prompt=prompt, max_tokens=max_tokens, temperature=temperature, is_async=is_async
    )


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
    ただし、anyio.run()で実行されたイベントループから別のanyio.run()を呼んではいけない。
    flexible_run()を使うことで、イベントループの状態に応じて適切な方法で非同期関数を実行できます。

    ## 間違わないための理解ポイント：
    awaitは非同期関数内で使う必要がある。非同期関数を呼び出すときは、awaitを忘れない。
    同期と非同期を正しく橋渡しするために、anyioのrun系関数（anyio.runやto_thread.run_sync）を使う。
    """

    # Model constants
    DEFAULT_MODEL_GEMINI = "gemini/gemini-1.5-flash-latest"
    DEFAULT_MODEL_CLAUDE = "claude-3-haiku-20240307"

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

        self._router = Router(
            model_list=model_list, fallbacks=fallbacks_dict, retry_after=3, num_retries=2, max_fallbacks=3
        )
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
                "rpm": RPM_LIMITS["other"],
                "tpm": TPM_LIMITS["other"],
            },
        }

        fallback_models = [
            {
                "model_name": "gemini_bkup1",
                "litellm_params": {
                    "model": self.DEFAULT_MODEL_GEMINI,
                    "api_key": os.getenv("GEMINI_API_KEY"),
                    "rpm": RPM_LIMITS["gemini_flash"],
                    "tpm": TPM_LIMITS["gemini_flash"],
                },
            },
            {
                "model_name": "gemini_bkup2",
                "litellm_params": {
                    "model": self.DEFAULT_MODEL_GEMINI,
                    "api_key": os.getenv("GEMINI_API_KEY2"),
                    "rpm": RPM_LIMITS["gemini_flash"],
                    "tpm": TPM_LIMITS["gemini_flash"],
                },
            },
            {
                "model_name": "claude_bkup",
                "litellm_params": {
                    "model": self.DEFAULT_MODEL_CLAUDE,
                    "api_key": os.getenv("ANTHROPIC_API_KEY"),
                    "rpm": RPM_LIMITS["anthropic_claude"],
                    "tpm": TPM_LIMITS["anthropic_claude"],
                },
            },
        ]

        # 全モデルを配列に入れて返す
        return [base_model, *fallback_models]

    @staticmethod
    def _create_fallbacks_dict() -> list[dict]:
        """Create fallback configuration.
        Fallbacks are done in-order ["model_a", "model_b", "model_c"], will do 'model_a' first, then 'model_b', etc.
        https://docs.litellm.ai/docs/routing
        """
        return [
            {"main": ["gemini_bkup1", "gemini_bkup2", "claude_bkup"]},
            {"gemini_bkup1": ["claude_bkup"]},
            {"gemini_bkup2": ["claude_bkup"]},
            {"gemini/gemini-1.5-flash": ["claude_bkup"]},  # 上手くFallbackが効かないので暫定
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
        if not await anyio.to_thread.run_sync(self._validate_input, prompt, max_tokens):
            return ""

        log("is_async=%s", is_async)
        if is_async:
            # Async call
            return await self._generate_async(model, prompt, max_tokens, temperature)
        # Sync call
        return await anyio.to_thread.run_sync(self._generate_sync, model, prompt, max_tokens, temperature)

    def _validate_input(self, prompt: str, max_tokens: int) -> bool:
        """Validate input parameters."""
        if not prompt.strip():
            log_w("Empty prompt received")
            return False

        prompt_length = len(prompt)
        if int(prompt_length * 0.5) > max_tokens:
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
        log_head("prompt", prompt, 1000)
        return await anyio.to_thread.run_sync(self._process_response, response, prompt)

    def _generate_sync(
        self,
        model: str,
        prompt: str,
        max_tokens: int,
        temperature: float,
        is_first_try: bool = True,  # noqa: FBT001
    ) -> str:
        """Handle sync response generation."""
        router = self._get_router(model)
        response = router.completion(
            model=model,
            messages=[{"content": prompt, "role": "user"}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return self._process_response(response=response, prompt=prompt, is_first_try=is_first_try)

    def _process_response(self, response: ModelResponse, prompt: str, is_first_try: bool = True) -> str:  # noqa: FBT001
        """Process and validate response."""
        if not response.choices or not response.choices[0].message or not response.choices[0].message.content:
            log_w("Invalid response received.")
            # 最後の手段で別modelで再度リクエストを送る
            if is_first_try:
                log_w("Invalid response is handled by retry with model: %s", self.DEFAULT_MODEL_CLAUDE)
                return self._generate_sync(self.DEFAULT_MODEL_CLAUDE, prompt, settings.max_tokens_any, 1.0, False)
            log_w("Invalid response is not recovered. prompt: %s", prompt)
            return ""
        response_text = response.choices[0].message.content.strip()
        log_head("response_text", response_text, 1000)
        return response_text

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
