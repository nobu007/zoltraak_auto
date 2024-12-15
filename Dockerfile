# Python 3.11をベースイメージとして使用
FROM python:3.11-slim

# 必要なシステム依存関係のインストール
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    graphviz \
    graphviz-dev \
    && rm -rf /var/lib/apt/lists/*

# 非rootユーザーの作成
RUN useradd -m -s /bin/bash appuser

# 作業ディレクトリの設定
WORKDIR /app

# ディレクトリの所有権変更
RUN chown -R appuser:appuser /app

# ユーザーの切り替え
USER appuser

# Poetryのインストール
RUN pip install poetry

# Poetryのパスを環境変数に追加
ENV PATH="/home/appuser/.local/bin:$PATH"

# プロジェクトのソースコードをコピー
COPY --chown=appuser:appuser . .

# Poetryの設定と依存関係のインストール
RUN poetry config virtualenvs.create true && \
    poetry config virtualenvs.in-project true && \
    poetry install --with test,lint --no-interaction --no-ansi

# PATHの更新
ENV PATH="/app/.venv/bin:$PATH"

# デフォルトコマンド
CMD ["bash"]