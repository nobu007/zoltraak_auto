import os
import pprint
from pathlib import Path

import zoltraak
from zoltraak.analyzer.dependency_map.change_impact_analyzer import ChangeImpactAnalyzer
from zoltraak.analyzer.dependency_map.dependency_visualizer import DependencyVisualizer
from zoltraak.analyzer.dependency_map.llm_context_generator import LLMContextGenerator
from zoltraak.analyzer.dependency_map.python.dependency_manager_py import DependencyManagerPy


def handle_file_change(file_path: Path, new_content: str, root_dir: str = ""):
    # 依存関係マネージャーを初期化
    if not root_dir:
        root_dir = Path.cwd()
    dm = DependencyManagerPy(root_dir)
    dm.scan_project()

    # 変更の影響を分析
    analyzer = ChangeImpactAnalyzer(dm)
    impact = analyzer.analyze_change(file_path, new_content)

    # 可視化
    viz = DependencyVisualizer()
    diagram = viz.create_diagram(dm, file_path)

    # LLMコンテキスト生成
    context_gen = LLMContextGenerator(dm)
    llm_context = context_gen.generate_context(file_path)

    return {"impact_analysis": impact, "dependency_diagram": diagram, "llm_context": llm_context}


if __name__ == "__main__":
    zoltraak_dir = os.path.dirname(zoltraak.__file__)

    file_path_ = __file__
    print("file_path_=", file_path_)
    # 実験: ファイル変更をシミュレート
    new_content_ = ""
    with open(file_path_, encoding="utf-8") as f:
        new_content_ = f.read()
        new_content_ = new_content_.replace("DependencyManagerPy", "DependencyManagerJava")
    result = handle_file_change(file_path_, new_content_, zoltraak_dir)
    print("result=")
    print("len=", len(pprint.pformat(result)))
