import ast
import datetime
import importlib.util
import os
import sys
from pathlib import Path

from networkx.drawing import nx_agraph

from zoltraak.analyzer.dependency_map.ast_util import ast_parse
from zoltraak.analyzer.dependency_map.dependency_manager_base import DependencyManagerBase
from zoltraak.analyzer.dependency_map.dependency_types import FileMetadata


class DependencyManagerPy(DependencyManagerBase):
    def __init__(self, project_root):
        super().__init__(project_root)

    def _analyze_file(self, file_path: Path) -> None:
        """個別ファイルの解析"""
        print("file_path=", file_path)

        # プロジェクトルートを追加
        self._add_project_path(file_path)

        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # ASTを使用して依存関係を抽出
        tree = ast_parse(content)
        import_map = self._extract_imports(tree, file_path)
        print("import_map=", import_map)

        # メタデータを抽出（docstringから）
        metadata = self._extract_metadata(tree)

        # グラフに追加
        include_files = []  # file_pathがimportするファイルのリスト
        included_files = []  # file_pathをimportする他のファイルのリスト #TODO: 未実装
        self.nx_graph.add_node(file_path)
        for org_file_path, dst_file_path in import_map.items():
            include_files.append(dst_file_path)
            self.nx_graph.add_edge(org_file_path, dst_file_path)

        # メタデータを保存
        self.metadata[file_path] = FileMetadata(
            path=file_path,
            last_modified=datetime.datetime.fromtimestamp(file_path.stat().st_mtime, tz=datetime.timezone.utc),  # noqa: UP017
            include_files=set(include_files),
            included_files=set(included_files),
            tags=metadata.get("tags", set()),
            category=metadata.get("category", "unknown"),
            description=metadata.get("description", ""),
        )

        # 画像として保存
        output_path_name = os.path.basename(file_path)
        output_path_path = os.path.join("out_png", "dependency_graph_all_" + output_path_name + ".png")
        os.makedirs("out_png", exist_ok=True)
        self._draw_dependency_graph(output_path_path)

    def _extract_imports(self, tree: ast.AST, file_path: Path) -> set[str]:
        """ASTからimport文を抽出"""
        import_map = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    resolved_path = self._resolve_import_path(alias.name, file_path)
                    if resolved_path:
                        import_map[file_path] = resolved_path

            elif isinstance(node, ast.ImportFrom):
                module = node.module if node.module else ""
                for alias in node.names:
                    full_name = f"{module}.{alias.name}" if module else alias.name
                    resolved_path = self._resolve_import_path(full_name, file_path)
                    if resolved_path:
                        import_map[file_path] = resolved_path

        return import_map

    def _draw_dependency_graph(self, output_path: str = "dependency_graph_all.png"):
        """依存関係の図を生成し、画像ファイルに保存"""
        agraph = nx_agraph.to_agraph(self.nx_graph)

        # レイアウトアルゴリズムの選択
        # prog=dot  # 階層的レイアウト（デフォルト）
        # prog=neato  # スプリングモデル
        # prog=fdp  # スプリングモデル（大規模グラフ向け）
        # prog=circo # 円形レイアウト
        # prog=twopi # 放射状レイアウト
        # prog=sfdp  # 多次元スケーリング
        prog = "neato"

        # 基本的なレイアウト制御
        if prog != "dot":
            agraph.draw(
                output_path,
                prog=prog,
                args="""
                    -Gdpi=600
                    -Gsize="10,10!"
                    -Goverlap=false
                    -Gsplines=true
                    -Gsep="+10"
                    """,
            )
        else:  # 階層的レイアウト（dot）の場合のオプション
            agraph.draw(
                output_path,
                prog=prog,
                args="""
                    -Gdpi=600
                    -Gsize="10,10!"
                    -Grankdir=LR
                    -Granksep=2.0
                    -Gnodesep=1.0
                    """,
            )

        # 個別のノード位置を指定
        # A.get_node("node1").attr["pos"] = "100,100!"  # 特定のノードの位置を固定
        # A.get_node("node2").attr["pos"] = "200,200!"

        # ノードの属性を設定
        # https://networkx.org/documentation/stable/reference/generated/networkx.drawing.nx_pylab.draw_networkx_nodes.html
        # ノードの形: shape[so^>v<dph8]
        #   s: square, o: circle, ^: triangle, >: triangle_right, v: triangle_down
        #   <: triangle_left, d: diamond, p: pentagon, h: hexagon, 8: octagon
        agraph.node_attr.update(
            shape="s",  # ノードの形
            # width="0.8",  # ノードの幅
            height="0.8",  # ノードの高さ
            fixedsize="false",  # サイズを固定
        )

        # 特定のノードをグループ化（サブグラフ作成）
        # subgraph = A.add_subgraph(["node1", "node2"], name="cluster_0")
        # subgraph.graph_attr["style"] = "filled"
        # subgraph.graph_attr["color"] = "lightgrey"
        # A.draw(output_path, prog="dot")

    def _resolve_import_path(self, import_name: str, current_file: Path) -> Path | None:
        """
        import文の文字列をファイルパスに解決する

        Args:
            import_name: 'package.module' 形式のimport文字列
            current_file: 解析対象のPythonファイルのパス
        """

        try:
            # まずsys.pathにある場所から探す
            spec = importlib.util.find_spec(import_name)
            if spec and spec.origin and self._is_valid_path(str(spec.origin)):
                return Path(spec.origin)

            # 相対インポートの場合は現在のファイルからの相対パスを考慮
            parts = import_name.split(".")
            possible_paths = [
                # 同じディレクトリから探す
                current_file.parent / f"{parts[-1]}.py",
                # パッケージとして探す
                current_file.parent / parts[-1] / "__init__.py",
            ]

            for path in possible_paths:
                if path.exists() and self._is_valid_path(str(path)):
                    return path

        except (ImportError, AttributeError):
            pass

        return None

    def _is_valid_path(self, file_path: str) -> bool:
        # フィルタキーワード
        filter_keywords = [".py"]
        if not any(keyword in file_path for keyword in filter_keywords):
            return False

        # 除外キーワード(.git配下は対象外など)
        ignore_keywords = [".git", ".pyenv", "__pycache__", "__init__.py", "site-packages", "built-in"]
        if any(keyword in str(file_path) for keyword in ignore_keywords):
            return False

        return True

    def _get_project_root(self, file_path: Path) -> Path:
        """プロジェクトのルートディレクトリを推測"""
        current = file_path.parent
        while current != current.parent:
            if (current / "setup.py").exists() or (current / "pyproject.toml").exists():
                return current
            current = current.parent
        return file_path.parent

    def _add_project_path(self, file_path: Path):
        """一時的にプロジェクトパスをsys.pathに追加"""
        project_root = self._get_project_root(file_path)
        sys.path.insert(0, str(project_root))
        return project_root
