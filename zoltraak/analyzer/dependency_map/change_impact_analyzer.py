import difflib
from pathlib import Path

from zoltraak.analyzer.dependency_map.dependency_manager_base import DependencyManagerBase
from zoltraak.analyzer.dependency_map.dependency_types import ChangeImpactResult


class ChangeImpactAnalyzer:
    def __init__(self, dependency_manager: DependencyManagerBase):
        self.dm = dependency_manager

    def analyze_change(self, file_path: Path, new_content: str) -> ChangeImpactResult:
        """変更の影響範囲を分析"""
        with open(file_path, encoding="utf-8") as f:
            old_content = f.read()

        # 差分を解析
        diff = difflib.unified_diff(old_content.splitlines(), new_content.splitlines())

        # 影響を受けるファイルを特定
        affected_files = self.dm.find_affected_files(file_path)

        # 必要なテストを特定
        tests_to_run = self.dm.suggest_test_targets(file_path)

        return ChangeImpactResult(affected_files=affected_files, tests_to_run=tests_to_run, diff_summary=list(diff))
