import difflib

from zoltraak.utils.log_util import log_head


class DiffUtil:
    @staticmethod
    def diff0(content1: list[str], content2: list[str]) -> str:
        if isinstance(content1, str):
            content1 = content1.split("\n")
        if isinstance(content2, str):
            content2 = content2.split("\n")

        diff_result = difflib.unified_diff(content1, content2, lineterm="", n=0)
        diff_result_txt = "\n".join(diff_result)
        log_head("diff_result_txt", diff_result_txt)
        return diff_result_txt

    @staticmethod
    def is_same_ignore_space(content1: str, content2: str) -> bool:
        diff_ignore_space = DiffUtil.diff0_ignore_space(content1, content2)
        return diff_ignore_space == ""

    @staticmethod
    def is_contain_ignore_space(content1: str, content2: str) -> bool:
        """content1 contains content2 => True

        Args:
            content1 (str): all_contents
            content2 (str): parts_contents

        Returns:
            bool: content2_ignored_str in content1_ignored_str
        """
        content1 = content1.strip()
        content2 = content2.strip()
        content1_ignored_list = DiffUtil.get_strip_space(content1)
        content2_ignored_list = DiffUtil.get_strip_space(content2)
        content1_ignored_str = "\n".join(content1_ignored_list)
        content2_ignored_str = "\n".join(content2_ignored_list)
        return content2_ignored_str in content1_ignored_str

    @staticmethod
    def diff0_ignore_space(content1: str, content2: str) -> str:
        content1 = content1.strip()
        content2 = content2.strip()
        content1_ignored_list = DiffUtil.get_strip_space(content1)
        content2_ignored_list = DiffUtil.get_strip_space(content2)
        return DiffUtil.diff0(content1_ignored_list, content2_ignored_list)

    @staticmethod
    def get_strip_space(content: str) -> list[str]:
        content_lines = content.split("\n")
        content_lines_strip_space_list = [line.strip() for line in content_lines]
        content_lines_ignore_empty_list = [line for line in content_lines_strip_space_list if line != ""]
        log_head("get_strip_space", "\n".join(content_lines_ignore_empty_list))
        return content_lines_ignore_empty_list
