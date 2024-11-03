# 作業内容
**`要件定義書`を元に、以下の指示に従ってPythonでディレクトリ構成を構築するコードを記述してください。コードのみ**

# モジュール情報
以下出力pythonファイル冒頭に記載すること
from zoltraak.llms.litellm_api import `generate_response`
from zoltraak.utils.process_text import `normal`

## 指示
1. コードブロックは使用せず、Pythonコードでディレクトリとファイルの構成を作成する
2. ディレクトリ構成は `ルートディレクトリ` =root_dir の配下にすべて作成すること（README.md を除いて、それ以外のファイルを記述）
    2.1 os.mkdirsを使用して`ルートディレクトリ`を作成する
    2.2 os.path.joinとos.makedirsを使用して、詳細なディレクトリ構成を作成する
    ディレクトリ名をリストに記述し実行
    2.3 作成するファイルの情報を作成する
    以下参考、ただしメインファイルはプログラムを詳細に記載する
    ```
    files = [
    ('dirname', 'filename', 'prompt'),
    ]
    ```
    補足説明:
    ・dirname: ディレクトリ名(root_dirからの相対パス)※ファイル名を含まない
    ・filename: ファイル名(拡張子あり)
    ・prompt: ファイル作成のためのプロンプト
    prompt部分は最重要かつ複雑なので順を追って説明する。注意深く正確な作業をお願いしたい。
    ・prompt部分はllmに渡されるプロンプトのファイル固有情報の説明である
    ・個々のファイルを正しく生成するために必要な情報を全て含めること(例: ～のためのユーティリティ関数で、書き込み・読み込みの機能を持つ)
    ・ファイル名と拡張子に注意すること
    ・promptの末尾は「～～を記載して下さい。」という形式にする
    ・`要件定義ファイル`の内容、dirname、filenameは固定で入れるので記載不要
    2.4 要件定義ファイルの内容を変数 readme_content に格納
        - `要件定義ファイル`の内容を読み込みモードで開く
    2.5 ルートディレクトリにREADME.mdファイルを書き込む
        - `要件定義ファイル`の内容をREADME.mdに書き込む
    2.6 必要なそれぞれのファイルの中身を作成する
    - tqdmのプログレスバーを利用
        プログレスバーを初期化。合計処理ファイル数: len(files)、単位: "files"、file=sys.stdout
        filesリストの要素を順にループ。各要素は (ディレクトリ名, ファイル名, プロンプト) のタプル
            モジュール記載忘れないように
            全てのファイルは`generate_response(model, prompt, max_tokens, temperature)`をもちいてfor文で然るべき内容を記載
                - モデル名を指定: "gemini/gemini-1.5-flash"
                - プロンプト: readme_content + 改行 + "上記の内容をもとにして" + prompt
                - 最大トークン数を指定: 12800
                - 温度パラメータを指定: 1.0
            出力結果は normal(response, "python")   にて加工して
        フォーマットしたレスポンスをファイルに書き込む
3. 生成したコードは即座に実行可能な状態にすること
4. 出力先ファイルはpythonであり、プログラムコードのみを記載し文言はコメントアウトで記載すること
    必ず冒頭に以下を入れること
    from zoltraak.llms.litellm_api import `generate_response`
    from zoltraak.utils.process_text import `normal`

# 引用
- `要件定義書` = [source_content]
- `要件定義書ファイル` = [source_file_path]
- `ルートディレクトリ` = generated/[source_file_name]/


# README.mdファイルのパスを作成
# README.mdファイルを書き込みモードで開く
# 要件定義ファイルを読み込みモードで開く
# - 要件定義ファイルのパスを指定
# -
# -- 要件定義ファイルの内容をREADME.mdに書き込む
# -- 要件定義ファイルの内容を変数 readme_content に格納

# プログレスバーを初期化
# filesリストの要素を順にループ
# - ファイルのパスを作成
# - ファイルを書き込みモードで開く
# -- LLMを使用してレスポンスを生成
# --- モデル名を指定
プロンプトを作成 {readme_content} + \n dirname={dirname} filename={filename}\n上記の内容をもとにして{prompt}
# --- 最大トークン数を指定
# --- 温度パラメータを指定
# --
# -- レスポンスをフォーマットして変数に格納
# -- フォーマットしたレスポンスをファイルに書き込む
# - プログレスバーを更新
