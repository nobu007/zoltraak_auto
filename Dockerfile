# Python 3.11をベースイメージとして使用
FROM python:3.11-slim

# 必要なシステム依存関係のインストール
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    graphviz \
    graphviz-dev && \
    rm -rf /var/lib/apt/lists/*

# 非rootユーザーの作成
RUN useradd -m -s /bin/bash appuser

# 作業ディレクトリの設定
WORKDIR /app

# ディレクトリの所有権変更
RUN chown -R appuser:appuser /app

# appuserに/tmpを開放
RUN rm -rf /tmp
RUN mkdir /tmp
RUN chown appuser:appuser /tmp

# ユーザーの切り替え
USER appuser

# Poetryのパスを環境変数に追加
ENV PATH="/home/appuser/.local/bin:/app/.venv/bin:$PATH"

# Poetryのインストール
RUN pip install --no-cache-dir poetry

# プロジェクトのソースコードをコピー
COPY --chown=appuser:appuser . .

# Poetryの設定と依存関係のインストール
RUN poetry config virtualenvs.create true && \
    poetry config virtualenvs.in-project true && \
    poetry install --with test,lint --no-interaction --no-ansi

# ユーザーの切り替え
USER root

# Poetryのパスを環境変数に追加
ENV PATH="/root/.local/bin:/app/.venv/bin:$PATH"

# Poetryのインストール
RUN pip install --no-cache-dir poetry

# Poetryの設定と依存関係のインストール
RUN poetry config virtualenvs.create true && \
    poetry config virtualenvs.in-project true && \
    poetry install --with test,lint --no-interaction --no-ansi

# デフォルトコマンド
CMD ["bash"]
