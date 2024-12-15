import os
from collections import defaultdict
from contextlib import suppress
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, TypedDict

import anyio
import litellm
from litellm import ModelResponse, Router, completion
from litellm.integrations.custom_logger import CustomLogger
from pydantic import BaseModel

from zoltraak import settings
from zoltraak.utils.file_util import FileUtil
from zoltraak.utils.log_util import log, log_head, log_w

# デバッグ用(ローカル環境でのみ利用すること！)
os.environ["LITELLM_LOG"] = "ERROR"
litellm.set_verbose = False
litellm.suppress_debug_info = False

# athina
# litellm.success_callback = ["athina"]

# langfuse
# litellm.success_callback = ["langfuse"]
# litellm.failure_callback = ["langfuse"]


class EvalMetadata(TypedDict):
    title: str = ""
    description: str = ""
    score: float = 0.0

    @classmethod
    def new(cls, title: str = "", description: str = "", score: float = 0.0) -> "EvalMetadata":
        return {"title": title, "description": description, "score": score}


class LitellmMetadata(TypedDict):
    generation_id: str = "generation_id_N"
    generation_name: str = "generation_name_N"
    trace_metadata: EvalMetadata = EvalMetadata()
    score: float = 0.1234

    @classmethod
    def new(
        cls,
        generation_id: str = "",
        generation_name: str = "",
        trace_metadata: EvalMetadata = None,
        score: float = 0.0,
    ) -> "LitellmMetadata":
        if trace_metadata is None:
            trace_metadata = EvalMetadata.new(score=score)

        local_tz = datetime.now().astimezone().tzinfo
        now_str = datetime.now(tz=local_tz).strftime("%Y%m%d_%H%M%S")

        if not generation_id:
            generation_id = now_str + "_litellm"
        if not generation_name:
            generation_name = "litellm"
        return {
            "generation_id": generation_id,
            "generation_name": generation_name,
            "trace_metadata": trace_metadata,
            "score": score,
        }


class LitellmMessage(TypedDict):
    content: str  # prompt
    role: str  # "user" or "system"

    @classmethod
    def new(cls, prompt: str) -> "LitellmMessage":
        return cls(content=prompt, role="user")


class LitellmParams(TypedDict):
    model: str
    messages: list[LitellmMessage]
    max_tokens: int
    temperature: float
    metadata: LitellmMetadata

    @classmethod
    def new(
        cls, prompt: str, model: str = settings.model_name, max_tokens: int = 4000, temperature=1.0, metadata=None
    ) -> "LitellmParams":
        if metadata is None:
            metadata = LitellmMetadata.new()
        messages = [LitellmMessage.new(prompt)]
        return cls(model=model, messages=messages, max_tokens=max_tokens, temperature=temperature, metadata=metadata)


class ModelStatsLogger(CustomLogger):
    def __init__(self):
        self.stats = defaultdict(lambda: {"count": 0, "total_tokens": 0, "start_time": None, "end_time": None})

    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        duration_time = end_time - start_time
        log_w("log_success_event duration_time=%s", duration_time)
        return self.update_stats(kwargs, response_obj, start_time, end_time)

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        duration_time = end_time - start_time
        log_w("async_log_success_event duration_time=%s", duration_time)
        return self.update_stats(kwargs, response_obj, start_time, end_time)

    def update_stats(self, kwargs, response_obj, start_time, end_time):
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
    "gemini": RPM_GEMINI_FLASH,
    "gemini_flash": RPM_GEMINI_FLASH,
    "gemini_pro": RPM_GEMINI_PRO,
    "claude": RPM_ANTHROPIC_CLAUDE,
    "other": RPM_OTHER,
}
TPM_LIMITS: dict = {
    "gemini": TPM_GEMINI_FLASH,
    "gemini_flash": TPM_GEMINI_FLASH,
    "gemini_pro": TPM_GEMINI_PRO,
    "claude": TPM_ANTHROPIC_CLAUDE,
    "other": TPM_OTHER,
}


@dataclass
class LitellmModelParams:
    model: str
    api_key: str
    rpm: str
    tpm: str


@dataclass
class ModelConfig:
    model_name: str
    litellm_params: LitellmModelParams


# 旧方式
# def flexible_run(async_func: callable, *args, **kwargs) -> Any:
#     """
#     コンテキストに応じて適切な方法で非同期関数を実行する
#     """
#     try:
#         with suppress(RuntimeError):
#             # 現在のイベントループでのタスクを取得しようとする
#             anyio.get_current_task()
#             return anyio.from_thread.run(async_func, *args, **kwargs)

#         # イベントループが存在しない場合は、新しいイベントループを作成して非同期関数を実行する
#         return anyio.run(async_func, *args, **kwargs)
#     except Exception as e:
#         # エラーハンドリング
#         print(f"Error executing async function: {e}")
#         raise


# 旧方式
def generate_response(
    model: str,
    prompt: str,
    max_tokens: int = 4000,
    temperature: float = 0.0,
    *,
    is_async: bool = False,
) -> str:
    api = LitellmApi()
    litellm_params = LitellmParams.new(prompt=prompt, model=model, max_tokens=max_tokens, temperature=temperature)
    return api.generate_response(litellm_params=litellm_params, is_async=is_async)


# 旧方式
async def generate_response_async(
    model: str,
    prompt: str,
    max_tokens: int = 4000,
    temperature: float = 0.0,
    is_async: bool = False,  # noqa: FBT001
) -> str:
    api = LitellmApi()
    litellm_params = LitellmParams.new(prompt=prompt, model=model, max_tokens=max_tokens, temperature=temperature)
    return await api.generate_response_async(litellm_params=litellm_params, is_async=is_async)


def generate_response_raw(
    model: str,
    prompt: str,
    max_tokens: int = 4000,
    temperature: float = 0.0,
    api_key: str = "",
    metadata: LitellmMetadata = None,
    response_format: type[BaseModel] | None = None,
) -> str:
    if metadata is None:
        metadata = LitellmMetadata.new()

    response = completion(
        model=model,
        messages=[{"content": prompt, "role": "user"}],
        max_tokens=max_tokens,
        temperature=temperature,
        api_key=api_key,
        num_retries=5,  # times
        cooldown_time=30,  # [s]
        metadata=metadata,
        response_format=response_format,
    )
    response_text = response.choices[0].message.content.strip()
    log_head("response_text", response_text)
    return response_text


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
    DEFAULT_MODEL_ANTHROPIC = "claude-3-haiku-20240307"
    DEFAULT_MODEL_GROQ = "groq/llama-3.1-70b-versatile"  # TODO: use "llama-3.2-11b-vision-preview"
    DEFAULT_MODEL_MISTRAL = "mistral/mistral-large-2407"

    def __init__(self, logger: ModelStatsLogger = logger_):
        self.logger = logger
        self._router: Router | None = None
        self.api_key_dict = {}

    def _get_router(self, model: str) -> Router:
        """Initialize and return a router with proper configuration."""

        # TODO: primary_modelによって動的にルーターを切り替える必要がありそう
        if self._router:
            return self._router

        model_config_list = self._create_model_list(primary_model=model)
        model_config_list_dict = [asdict(model) for model in model_config_list]
        fallbacks_dict = self._create_fallbacks_dict(model_config_list)

        self._router = Router(
            model_list=model_config_list_dict, fallbacks=fallbacks_dict, retry_after=10, num_retries=3, max_fallbacks=5
        )
        return self._router

    def _create_model_list(self, primary_model: str) -> list[ModelConfig]:
        """Create model list configuration including fallbacks."""

        # モデルとAPIキーの設定を動的に生成
        fallback_models = []
        model_names = os.getenv("API_MODELS").split(",")

        for model_name in model_names:
            keys_env_name = f"{model_name.upper()}_API_KEYS"
            api_keys = os.getenv(keys_env_name)
            if api_keys:
                for i, api_key in enumerate(api_keys.split(",")):
                    api_key_without_new_line = api_key.replace("\n", "")
                    fallback_models.append(  # noqa: PERF401
                        ModelConfig(
                            model_name=f"{model_name}_group_{i}",
                            litellm_params=LitellmParams(
                                model=getattr(self, f"DEFAULT_MODEL_{model_name.upper()}", "unknown"),
                                api_key=api_key_without_new_line,
                                rpm=RPM_LIMITS["other"],
                                tpm=TPM_LIMITS["other"],
                            ),
                        )
                    )
                    self.api_key_dict[model_name] = api_key

        # primary_modelのapi_keyが存在しない場合はデフォルトを設定
        if primary_model not in self.api_key_dict:
            primary_model = self.DEFAULT_MODEL_GEMINI
            self.api_key_dict[primary_model] = self.api_key_dict["gemini"]

        # ベースモデルの設定
        base_model = ModelConfig(
            model_name="main",
            litellm_params=LitellmModelParams(
                model=primary_model,
                api_key=self.api_key_dict[primary_model],
                rpm=RPM_LIMITS["other"],
                tpm=TPM_LIMITS["other"],
            ),
        )

        # 全モデルをリストにして返す
        return [base_model, *fallback_models]

    @staticmethod
    def _create_fallbacks_dict(model_config_list: list[ModelConfig]) -> list[dict]:
        """Create fallback configuration.
        Fallbacks are done in-order ["model_a", "model_b", "model_c"], will do 'model_a' first, then 'model_b', etc.
        https://docs.litellm.ai/docs/routing
        """

        # フォールバックリストを作成

        fallback_models = []
        for model_config in model_config_list:
            fallback_models.append(model_config.model_name)  # noqa: PERF401
        return [{"main": fallback_models}]

        # サンプル
        # return [
        #     {"main": ["gemini_group1", "gemini_group2", "mistral_group", "groq_group"]},
        #     {"gemini_group1": ["mistral_group", "groq_group"]},
        #     {"gemini_group2": ["mistral_group", "groq_group"]},
        #     {"gemini/gemini-1.5-flash": ["mistral_group", "groq_group"]},  # 上手くFallbackが効かないので暫定
        #     {LitellmApi.DEFAULT_MODEL_GEMINI: ["mistral_group", "groq_group"]},  # 上手くFallbackが効かないので暫定
        # ]

    def generate_response(self, litellm_params: LitellmParams, is_async: bool = False) -> Any:  # noqa: FBT001
        """
        コンテキストに応じて適切な方法でgenerate_response_asyncを実行する
        """
        try:
            with suppress(RuntimeError):
                # 現在のイベントループでのタスクを取得しようとする
                anyio.get_current_task()
                return anyio.from_thread.run(self.generate_response_async, litellm_params, is_async)

            # イベントループが存在しない場合は、新しいイベントループを作成して非同期関数を実行する
            return anyio.run(self.generate_response_async, litellm_params, is_async)
        except Exception as e:
            # エラーハンドリング
            print(f"Error executing async function: {e}")
            raise

    async def generate_response_async(
        self,
        litellm_params: LitellmParams,
        is_async: bool = False,  # noqa: FBT001
    ) -> str:
        """同期と非同期を共通の関数で呼べるようにした"""
        if not await anyio.to_thread.run_sync(self._validate_input, litellm_params):
            return ""

        log("is_async=%s", is_async)
        if is_async:
            # Async call
            return await self._generate_async(litellm_params)
        # Sync call
        return await anyio.to_thread.run_sync(self._generate_sync, litellm_params)

    def _validate_input(self, litellm_params: LitellmParams) -> bool:
        """Validate input parameters."""
        prompt = litellm_params["messages"][0]["content"]
        max_tokens = litellm_params["max_tokens"]

        if not prompt.strip():
            log_w("Empty prompt received")
            return False

        prompt_length = len(prompt)
        if int(prompt_length * 0.5) > max_tokens:
            log_w("WARN: max_tokens might be too small. prompt len=%s, max_tokens=%d", prompt_length, max_tokens)
            FileUtil.write_file(f"over_prompt_{prompt_length}.txt", prompt)

        return True

    async def _generate_async(self, litellm_params: LitellmParams) -> str:
        """Handle async response generation."""
        router = self._get_router(litellm_params["model"])
        response = await router.acompletion(**litellm_params)
        return await anyio.to_thread.run_sync(self._process_response, response, litellm_params)

    def _generate_sync(
        self,
        litellm_params: LitellmParams,
        is_first_try: bool = True,  # noqa: FBT001
    ) -> str:
        """Handle sync response generation."""
        router = self._get_router(litellm_params["model"])
        response = router.completion(**litellm_params)
        return self._process_response(response=response, litellm_params=litellm_params, is_first_try=is_first_try)

    def _process_response(
        self,
        response: ModelResponse,
        litellm_params: LitellmParams,
        is_first_try: bool = True,  # noqa: FBT001
    ) -> str:  # noqa: FBT001
        """Process and validate response."""
        if not response.choices or not response.choices[0].message or not response.choices[0].message.content:
            log_w("Invalid response received.")
            # 最後の手段で別modelで再度リクエストを送る
            litellm_params_copy = litellm_params.copy()
            litellm_params_copy["model"] = self.DEFAULT_MODEL_ANTHROPIC
            litellm_params_copy["max_tokens"] = settings.max_tokens_claude_haiku
            litellm_params_copy["metadata"]["generation_name"] = "retry"
            if is_first_try:
                log_w("Invalid response is handled by retry with model: %s", self.DEFAULT_MODEL_ANTHROPIC)
                return self._generate_sync(litellm_params_copy, False)
            log_w("Invalid response is not recovered. prompt: %s", litellm_params["messages"][0]["content"])
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
