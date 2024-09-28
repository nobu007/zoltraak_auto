import shlex
import subprocess
from typing import Any


class SubprocessUtil:
    CompletedProcess = subprocess.CompletedProcess

    @staticmethod
    def quote(s: str | list[str]) -> str | list[str]:
        """
        Safely quote a string or list of strings for use in shell commands.

        Args:
            s (str | list[str]): The string or list of strings to quote.

        Returns:
            str | list[str]: The quoted string or list of strings.
        """
        if isinstance(s, list):
            return [shlex.quote(arg) for arg in s]
        return shlex.quote(s)

    @staticmethod
    def split(command: str) -> list[str]:
        """
        Split a command string into a list of arguments.

        Args:
            command (str): The command string to split.

        Returns:
            list[str]: The list of command arguments.
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
        Run a command in a subprocess.

        Args:
            args (Union[str, list[str]]): The command to run. If a string, it will be split.
            cwd (Optional[str]): The working directory for the command.
            env (Optional[Dict[str, str]]): Environment variables for the new process.
            shell (bool): If True, the command will be executed through the shell.
            timeout (Optional[float]): If the process does not terminate after timeout seconds,
                raise a TimeoutExpired exception.
            check (bool): If True, raise a CalledProcessError if the exit code is non-zero.
            capture_output (bool): If True, stdout and stderr will be captured.
            text (bool): If True, decode stdout and stderr using the specified encoding.
            encoding (Optional[str]): The encoding to use for text mode operations.
            errors (Optional[str]): The error handling scheme to use for decoding.

        Returns:
            subprocess.CompletedProcess: A CompletedProcess instance.

        Raises:
            subprocess.CalledProcessError: If check is True and the process returns a non-zero exit status.
            subprocess.TimeoutExpired: If the timeout expires.
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
        Run a shell command safely.

        This method is a wrapper around the run method, specifically for shell commands.
        It automatically sets shell=True and uses shlex.quote for safety.

        Args:
            command (str): The shell command to run.
            cwd (Optional[str]): The working directory for the command.
            env (Optional[Dict[str, str]]): Environment variables for the new process.
            timeout (Optional[float]): If the process does not terminate after timeout seconds, raise a TimeoutExpired exception.
            check (bool): If True, raise a CalledProcessError if the exit code is non-zero.
            capture_output (bool): If True, stdout and stderr will be captured.

        Returns:
            subprocess.CompletedProcess: A CompletedProcess instance.

        Raises:
            subprocess.CalledProcessError: If check is True and the process returns a non-zero exit status.
            subprocess.TimeoutExpired: If the timeout expires.
        """
        sanitized_command = SubprocessUtil.sanitize_command(command)
        if show_command:
            print("sanitized_command=", sanitized_command)
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
