import shlex
import subprocess
from typing import Any

from zoltraak.utils.log_util import log


class SubprocessUtil:
    CompletedProcess = subprocess.CompletedProcess

    @staticmethod
    def quote(s: str | list[str]) -> str | list[str]:
        """
        文字列または文字列のリストをシェルコマンド用に安全にクオートします。

        引数:
            s (str | list[str]): クオートする文字列または文字列のリスト。

        戻り値:
            str | list[str]: クオートされた文字列または文字列のリスト。
        """
        if isinstance(s, list):
            return [shlex.quote(arg) for arg in s]
        return shlex.quote(s)

    @staticmethod
    def split(command: str) -> list[str]:
        """
        コマンド文字列を引数のリストに分割します。

        引数:
            command (str): 分割するコマンド文字列。

        戻り値:
            list[str]: コマンド引数のリスト。
        """
        return shlex.split(command)

    @staticmethod
    def run(
        args: str | list[str],
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        encoding: str = "utf-8",
        errors: str | None = None,
        timeout: float | None = None,
        *,  # ↑位置引数(args=とか省略可) ココから後はキーワード引数↓
        text: bool = True,
        capture_output: bool = False,
        check: bool = True,
        shell: bool = False,
    ) -> subprocess.CompletedProcess:
        """
        サブプロセスでコマンドを実行します。

        引数:
            args (str または list[str]): 実行するコマンド。文字列の場合は分割されます。
            cwd (Optional[str]): コマンドの作業ディレクトリ。
            env (Optional[Dict[str, str]]): 新しいプロセスの環境変数。
            shell (bool): Trueの場合、シェルを通してコマンドを実行します。
            timeout (Optional[float]): プロセスがtimeout秒後に終了しない場合、TimeoutExpired例外を発生させます。
            check (bool): Trueの場合、終了コードが0以外ならCalledProcessErrorを発生させます。
            capture_output (bool): Trueの場合、stdoutとstderrをキャプチャします。
            text (bool): Trueの場合、指定されたエンコーディングを使用してstdoutとstderrをデコードします。
            encoding (Optional[str]): テキストモード操作に使用するエンコーディング。
            errors (Optional[str]): デコード時のエラーハンドリング方式。

        戻り値:
            subprocess.CompletedProcess: CompletedProcessインスタンス。

        例外:
            subprocess.CalledProcessError: checkがTrueで、プロセスが非ゼロの終了ステータスを返した場合。
            subprocess.TimeoutExpired: タイムアウトが発生した場合。
        """
        kwargs: dict[str, Any] = {
            "args": args,
            "cwd": cwd,
            "env": env,
            "shell": shell,
            "timeout": timeout,
            "capture_output": capture_output,
            "text": text,
            "encoding": encoding,
            "errors": errors,
        }

        # Remove None values to use default subprocess.run behavior
        kwargs = {k: v for k, v in kwargs.items() if v is not None}

        # Avoid W1510: https://pylint.readthedocs.io/en/latest/user_guide/messages/warning/subprocess-run-check.html
        return subprocess.run(**kwargs, check=check)

    @staticmethod
    def sanitize_command(command: str) -> str:
        """
        コマンド文字列にdangerous_charsが含まれていたら、
        処理を無効化して安全なコードに置き換えます。
        """
        dangerous_chars = [";", "$"]
        dangerous_chars_str = "".join(dangerous_chars)
        if any(char in command for char in dangerous_chars):
            command = f"echo '{dangerous_chars_str} を含むコマンドは許可されていないため無効化されました。'"
        return command

    @staticmethod
    def run_shell_command(
        command: str,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout: float | None = None,
        *,  # ↑位置引数(args=とか省略可) ココから後はキーワード引数↓
        check: bool = True,
        capture_output: bool = False,
        show_command: bool = False,
    ) -> subprocess.CompletedProcess:
        """
        シェルコマンドを安全に実行します。

        このメソッドはrunメソッドのラッパーで、特にシェルコマンド用です。
        自動的にshell=Trueを設定し、安全のためにshlex.quoteを使用します。

        Args:
            command (str): 実行するシェルコマンド。
            cwd (Optional[str]): コマンドの作業ディレクトリ。
            env (Optional[Dict[str, str]]): 新しいプロセスの環境変数。
            timeout (Optional[float]): タイムアウト秒数。タイムアウトした場合、TimeoutExpired例外を発生させます。
            check (bool): Trueの場合、終了コードが0以外ならCalledProcessErrorを発生させます。
            capture_output (bool): Trueの場合、stdoutとstderrをキャプチャします。

        Returns:
            subprocess.CompletedProcess: CompletedProcessインスタンス。

        Raises:
            subprocess.CalledProcessError: checkがTrueで、プロセスが非ゼロの終了ステータスを返した場合。
            subprocess.TimeoutExpired: タイムアウトが発生した場合。
        """
        sanitized_command = SubprocessUtil.sanitize_command(command)
        if show_command:
            log("sanitized_command=", sanitized_command)
        return SubprocessUtil.run(
            args=["/bin/sh", "-c", sanitized_command],
            cwd=cwd,
            env=env,
            shell=False,  # We're explicitly using /bin/sh, so shell=False
            timeout=timeout,
            check=check,
            capture_output=capture_output,
        )


if __name__ == "__main__":  # このスクリプトが直接実行された場合にのみ、以下のコードを実行します。
    SubprocessUtil.run(["echo", "ddd"], shell=False)
    # SubprocessUtil.run("echo eee", shell=True)
    SubprocessUtil.run_shell_command("ls | grep .py | xargs head -n 1")
    SubprocessUtil.run_shell_command("echo $DDD")
