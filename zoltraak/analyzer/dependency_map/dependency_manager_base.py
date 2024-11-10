import ast
from pathlib import Path

import networkx as nx

from zoltraak.analyzer.dependency_map.dependency_types import FileMetadata


class DependencyManagerBase:
    def __init__(self, project_root: Path | str):
        self.project_root = Path(project_root)
        self.nx_graph = nx.DiGraph()
        self.metadata: dict[Path, FileMetadata] = {}

    def scan_project(self) -> None:
        """プロジェクト全体をスキャンして依存関係を構築"""
        # 除外キーワード(.git配下は対象外など)
        ignore_keywords = [".git", "__pycache__", "__init__.py", "site-packages"]

        for file_path in self.project_root.rglob("*.py"):
            if any(keyword in str(file_path) for keyword in ignore_keywords):
                continue
            self._analyze_file(file_path)

    def find_affected_files(self, changed_file: Path) -> set[Path]:
        """変更されたファイルに影響を受けるファイルを特定"""
        try:
            return set(nx.descendants(self.nx_graph, changed_file))
        except nx.NetworkXError as e:
            print("Error in find_affected_files", e)
            return set()

    def suggest_test_targets(self, changed_file: Path) -> set[Path]:
        """変更に関連するテストファイルを提案"""
        affected = self.find_affected_files(changed_file)
        return {p for p in affected if p.stem.startswith("test_")}

    def get_metadata(self, file_path: Path) -> FileMetadata:
        """ファイルのメタデータを取得"""
        default_metadata = FileMetadata(path=file_path, last_modified=None)
        return self.metadata.get(file_path, default_metadata)

    def _analyze_file(self, file_path: Path) -> None:
        """個別ファイルの解析"""
        # TODO: 実装

    def _extract_metadata(self, tree: ast.AST) -> dict[str, str]:
        """ASTからメタデータを抽出
        TODO: python以外も対応
        """
        metadata = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "metadata":
                metadata = self._parse_metadata(node)
                break
        return metadata
