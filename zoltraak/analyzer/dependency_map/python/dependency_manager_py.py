import datetime
from pathlib import Path

from zoltraak.analyzer.dependency_map.ast_util import ast_parse
from zoltraak.analyzer.dependency_map.dependency_manager_base import DependencyManagerBase
from zoltraak.analyzer.dependency_map.dependency_types import FileMetadata


class DependencyManagerPy(DependencyManagerBase):
    def _analyze_file(self, file_path: Path) -> None:
        """個別ファイルの解析"""
        print("file_path=", file_path)
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # ASTを使用して依存関係を抽出
        print("content=", content)
        tree = ast_parse(content)
        imports = self._extract_imports(tree)

        # メタデータを抽出（docstringから）
        metadata = self._extract_metadata(tree)

        # グラフに追加
        self.graph.add_node(file_path)
        for imp in imports:
            self.graph.add_edge(file_path, imp)

        # メタデータを保存
        self.metadata[file_path] = FileMetadata(
            path=file_path,
            last_modified=datetime.datetime.fromtimestamp(file_path.stat().st_mtime, tz=datetime.timezone.utc),  # noqa: UP017
            dependencies=set(imports),
            dependents=set(),
            tags=metadata.get("tags", set()),
            category=metadata.get("category", "unknown"),
            description=metadata.get("description", ""),
        )
