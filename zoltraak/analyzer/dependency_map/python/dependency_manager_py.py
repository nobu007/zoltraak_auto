import datetime
import os
from pathlib import Path

from networkx.drawing import nx_agraph

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
        tree = ast_parse(content)
        imports = self._extract_imports(tree)
        print("imports=", imports)

        # メタデータを抽出（docstringから）
        metadata = self._extract_metadata(tree)

        # グラフに追加
        self.nx_graph.add_node(file_path)
        for imp in imports:
            self.nx_graph.add_edge(file_path, imp)

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

        # 画像として保存
        output_path_name = os.path.basename(file_path)
        output_path_path = os.path.join("out_png", "dependency_graph_all_" + output_path_name + ".png")
        os.makedirs("out_png", exist_ok=True)
        self._draw_dependency_graph(output_path_path)

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
        prog = "dot"

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
                    -Gdpi=1200
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
