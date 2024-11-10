from pathlib import Path

import pygraphviz as pgv

from zoltraak.analyzer.dependency_map.dependency_manager_base import DependencyManagerBase


class DependencyVisualizer:
    @staticmethod
    def create_diagram(
        manager: DependencyManagerBase, focus_file: Path | None, output_path: str = "dependency_graph.png"
    ) -> str:
        """依存関係の図を生成し、画像ファイルに保存"""
        graph = pgv.AGraph(directed=True)

        # 特定ファイルにフォーカスするか、全体の依存関係を表示するかを設定
        if focus_file:
            metadata_focus_file = manager.get_metadata(focus_file)
            relevant_files = {focus_file}
            relevant_files |= metadata_focus_file.include_files
            relevant_files |= metadata_focus_file.included_files
        else:
            relevant_files = set(manager.metadata.keys())

        # ノードの作成
        for file in relevant_files:
            metadata_file = manager.get_metadata(file)
            label = f"{file!s}\n{metadata_file.category}"
            graph.add_node(str(file), label=label)

        # エッジの作成(ノード作成完了後に実行する必要あり)
        for file in relevant_files:
            metadata_file = manager.get_metadata(file)
            for dep in metadata_file.include_files & relevant_files:
                graph.add_edge(str(file), str(dep))

        # 画像として保存
        graph.layout(prog="dot")
        graph.draw(output_path)

        return output_path
