import os
from os.path import dirname, join

from dotenv import load_dotenv

import zoltraak

load_dotenv(verbose=True)

dotenv_path = join(dirname(__file__), ".env")
load_dotenv(dotenv_path)


# api_key
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")  # 環境変数からAPI keyを取得
groq_api_key = os.getenv("GROQ_API_KEY")  # 環境変数からGroqのAPI keyを取得

# model_name
model_name = os.getenv("MODEL_NAME", "gemini/gemini-1.5-flash-latest")
model_name_lite = os.getenv("MODEL_NAME_LITE", model_name)  # 通常よりも簡単な処理用のllmモデル名
model_name_smart = os.getenv("MODEL_NAME_SMART", model_name)  # 通常よりも不雑な処理用のllmモデル名

# folder
zoltraak_dir = os.path.dirname(zoltraak.__file__)
zoltraak_dir = os.path.abspath(zoltraak_dir)
grimoires_dir = os.path.join(zoltraak_dir, "grimoires")
architects_dir = os.path.join(grimoires_dir, "architects")
compiler_dir = os.path.join(grimoires_dir, "compiler")
developer_dir = os.path.join(grimoires_dir, "developer")
encryption_dir = os.path.join(grimoires_dir, "encryption")
formatter_dir = os.path.join(grimoires_dir, "formatter")
interpretspec_dir = os.path.join(grimoires_dir, "interpretspec")

# mode
is_debug = False  # デバッグモード
