import os
from os.path import join, dirname
from dotenv import load_dotenv

load_dotenv(verbose=True)

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)


# api_key
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")  # 環境変数からAPI keyを取得
groq_api_key = os.getenv("GROQ_API_KEY")  # 環境変数からGroqのAPI keyを取得

# model_name
model_name = os.getenv("MODEL_NAME", "claude-3-haiku-20240307")
model_name_lite = os.getenv("MODEL_NAME_LITE", model_name) # 通常よりも簡単な処理用のllmモデル名
model_name_smart = os.getenv("MODEL_NAME_SMART", model_name) # 通常よりも不雑な処理用のllmモデル名
