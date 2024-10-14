# [システム名]のファイル・フォルダ構成（完全版）

plain txt で省略なしのディレクトリ、ファイル構成のみを記載してください。

## ゴール:

<goal_prompt>
{prompt}
</goal_prompt>

## 1. ファイル・フォルダ構成

- plain txt で省略なしのディレクトリ、ファイル構成
- ルートディレクトリから下層のディレクトリの中の複数ファイル名まで網羅的に記載（内容は必要なし）
- 空のディレクトリを作らない

## 2. 注意点

- 不明点があっても省略せずに完全なファイルパスを定義してください。
- pyproject.toml や README.md も省略せずに記載してください。
- フォルダの記載は不要です。

## 3. サンプル

次のようにファイルパスのみを列記してください。
後ほどプログラムでファイルリストを使って一括処理します。

```
InstantPromptBox/README.md
InstantPromptBox/pyproject.toml
InstantPromptBox/prompts/zoltraak/zoltraak_prompt_aaaa.md
InstantPromptBox/prompts/zoltraak/zoltraak_prompt_aaaa.py
InstantPromptBox/src/main.py
```
