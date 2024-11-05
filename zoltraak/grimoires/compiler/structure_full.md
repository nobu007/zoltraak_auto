# [システム名]のファイル・フォルダ構成（完全版）

plain txt で省略なしのディレクトリ、ファイル構成のみを記載してください。

## ゴール

<goal_prompt>
{prompt}
</goal_prompt>

## 1. ファイル・フォルダ構成

- plain txt で省略なしのディレクトリ、ファイル構成
- ルートディレクトリ(通常は generated)は省略し、直下のディレクトリからの相対パスで全ファイルを網羅的に記載（内容は必要なし）

## 2. 注意点

- 不明点があっても省略しないでください。
- pyproject.toml や README.md も省略せずに記載してください。
- フォルダの記載は不要です。

## 3. サンプル

次のようにファイルパスのみを列記してください。
後ほどプログラムでファイルリストを使って一括処理するのでミスなく正確にお願いします。

XXXX はシステムを一意に識別するための canonical_name です。
YYYY は python パッケージなどの最上位のサブフォルダです。

```plaintext
XXXX/pyproject.toml
XXXX/README.md
XXXX/YYYY/pyproject.toml
XXXX/YYYY/prompts/zoltraak/zoltraak_prompt_aaaa.md
XXXX/YYYY/prompts/zoltraak/zoltraak_prompt_aaaa.py
XXXX/YYYY/src/main.py
```
