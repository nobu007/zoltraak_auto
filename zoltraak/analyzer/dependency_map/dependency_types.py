from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TypedDict


@dataclass
class FileMetadata:
    path: Path
    last_modified: datetime
    dependencies: set[Path] = field(default_factory=set)
    dependents: set[Path] = field(default_factory=set)
    tags: set[str] = field(default_factory=set)
    category: str = ""
    description: str = ""


class ChangeImpactResult(TypedDict):
    affected_files: set[Path]
    tests_to_run: set[str]
    diff_summary: list[str]
