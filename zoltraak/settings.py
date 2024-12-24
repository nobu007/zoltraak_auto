import os
from os.path import dirname, join

from dotenv import load_dotenv

import zoltraak

load_dotenv(verbose=True)

dotenv_path = join(dirname(__file__), ".env")
load_dotenv(dotenv_path)


# api_keys(環境変数からAPI keyを取得)
api_models = os.getenv("API_MODELS")
gemini_api_keys = os.getenv("GEMINI_API_KEYS")
anthropic_api_keys = os.getenv("ANTHROPIC_API_KEYS")
groq_api_keys = os.getenv("GROQ_API_KEYS")
mistral_api_keys = os.getenv("MISTRAL_API_KEYS")

# api_key(api_keysから取得して環境変数に反映)
if gemini_api_keys:
    gemini_api_key = gemini_api_keys.split(",")[0]
    if gemini_api_key and not os.getenv("GEMINI_API_KEY"):
        os.environ["GEMINI_API_KEY"] = gemini_api_key
if anthropic_api_keys:
    anthropic_api_key = anthropic_api_keys.split(",")[0]
    if anthropic_api_key and not os.getenv("ANTHROPIC_API_KEY"):
        os.environ["ANTHROPIC_API_KEY"] = anthropic_api_key
if groq_api_keys:
    groq_api_key = groq_api_keys.split(",")[0]
    if groq_api_key and not os.getenv("GROQ_API_KEY"):
        os.environ["GROQ_API_KEY"] = groq_api_key
if mistral_api_keys:
    mistral_api_key = mistral_api_keys.split(",")[0]
    if mistral_api_key and not os.getenv("MISTRAL_API_KEY"):
        os.environ["MISTRAL_API_KEY"] = mistral_api_key

# model_name
model_name = os.getenv("MODEL_NAME_DEFAULT", "gemini/gemini-1.5-flash-latest")
model_name_lite = os.getenv("MODEL_NAME_LITE", model_name)  # 通常よりも簡単な処理用のllmモデル名
model_name_smart = os.getenv("MODEL_NAME_SMART", model_name)  # 通常よりも不雑な処理用のllmモデル名
print("model_name=", model_name)
print("model_name_lite=", model_name_lite)
print("model_name_smart=", model_name_smart)

# max_tokens
max_tokens_create_file_name = 100
max_tokens_generate_md = 8000
max_tokens_generate_code = 8000
max_tokens_generate_code_fix = 8000
max_tokens_generate_error_reason = 2000
max_tokens_get_match_rate = 4000
max_tokens_propose_diff = 4000
max_tokens_apply_diff = 8000
max_tokens_claude_haiku = 4000
max_tokens_any = 4000  # その他の場合

# temperature
temperature_create_file_name = 0.0
temperature_generate_md = 0.0
temperature_generate_code = 0.0
temperature_generate_code_fix = 0.0
temperature_generate_error_reason = 0.0
temperature_get_match_rate = 0.0
temperature_propose_diff = 0.0
temperature_apply_diff = 0.0
temperature_any = 0.0  # その他の場合

# folder
zoltraak_dir = os.path.dirname(zoltraak.__file__)
zoltraak_dir = os.path.abspath(zoltraak_dir)
grimoires_dir = os.path.join(zoltraak_dir, "grimoires")
architects_dir = os.path.join(grimoires_dir, "architect")
compiler_dir = os.path.join(grimoires_dir, "compiler")
developer_dir = os.path.join(grimoires_dir, "developer")
encryption_dir = os.path.join(grimoires_dir, "encryption")
formatter_dir = os.path.join(grimoires_dir, "formatter")
interpretspec_dir = os.path.join(grimoires_dir, "interpretspec")

# mode
is_debug = os.getenv("IS_DEBUG", "False").lower() in ("true", "1", "t")  # デバッグモード(例: IS_DEBUG=True)
