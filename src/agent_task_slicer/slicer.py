"""High-level slicing API."""

from __future__ import annotations

from typing import Optional

from .config import SlicerConfig
from .heuristics import enrich_tasks, identify_tasks
from .models import SliceResult
from .parser import parse_file, parse_text


class TaskSlicer:
    """Slice product/development requirements into agent-ready work packages."""

    def __init__(self, config: Optional[SlicerConfig] = None):
        self.config = config or SlicerConfig()

    def slice_text(self, text: str, source: str = "<text>") -> SliceResult:
        document = parse_text(text, source=source)
        tasks = identify_tasks(document, self.config)
        warnings = []
        if not tasks:
            warnings.append("No tasks were identified.")
        if len(tasks) >= self.config.max_tasks:
            warnings.append(f"Task output was limited to max_tasks={self.config.max_tasks}.")
        enriched = enrich_tasks(tasks, document, self.config)
        return SliceResult(
            source=document.source,
            tasks=enriched,
            warnings=warnings,
            metadata={"title": document.title, "sections": len(document.sections)},
        )

    def slice_file(self, path: str) -> SliceResult:
        document = parse_file(path)
        tasks = identify_tasks(document, self.config)
        warnings = []
        if not tasks:
            warnings.append("No tasks were identified.")
        if len(tasks) >= self.config.max_tasks:
            warnings.append(f"Task output was limited to max_tasks={self.config.max_tasks}.")
        enriched = enrich_tasks(tasks, document, self.config)
        return SliceResult(
            source=document.source,
            tasks=enriched,
            warnings=warnings,
            metadata={"title": document.title, "sections": len(document.sections)},
        )


def slice_text(text: str, config: Optional[SlicerConfig] = None, source: str = "<text>") -> SliceResult:
    """Convenience API for slicing raw text."""

    return TaskSlicer(config).slice_text(text, source=source)


def slice_file(path: str, config: Optional[SlicerConfig] = None) -> SliceResult:
    """Convenience API for slicing a local file."""

    return TaskSlicer(config).slice_file(path)

