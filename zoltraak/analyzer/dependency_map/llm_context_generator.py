from pathlib import Path

from zoltraak.analyzer.dependency_map.dependency_manager_base import DependencyManagerBase


class LLMContextGenerator:
    def __init__(self, dependency_manager: DependencyManagerBase):
        self.dependency_manager = dependency_manager

    def generate_context(self, target_file: Path) -> str:
        """LLM用のコンテキストを生成"""
        metadata = self.dependency_manager.get_metadata(target_file)

        # 関連ファイルを収集
        related_files = {target_file} | metadata.include_files | metadata.included_files

        # コンテキストを構築
        context = [
            "# Project Context",
            f"Target file: {target_file}",
            f"Category: {metadata.category}",
            f"Description: {metadata.description}",
            "\n# Related Files:",
        ]

        for file in related_files:
            rel_metadata = self.dependency_manager.get_metadata(file)
            context.append(f"\n## {file!s}")
            context.append(f"Category: {rel_metadata.category}")
            context.append(f"Description: {rel_metadata.description}")
            with open(file, encoding="utf-8") as f:
                # TODO: 暫定でpython専用コードとしているが、他言語にも対応する
                context.append("```python")
                context.append(f.read())
                context.append("```")

        return "\n".join(context)
