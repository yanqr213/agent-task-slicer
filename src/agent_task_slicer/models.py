"""Core data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class DocumentSection:
    """A heading-delimited Markdown section."""

    title: str
    level: int
    content: str
    start_line: int
    end_line: int
    path_hints: List[str] = field(default_factory=list)
    checklist_items: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class Document:
    """Parsed input document."""

    source: str
    title: str
    raw_text: str
    sections: List[DocumentSection]
    path_hints: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class AcceptanceCriterion:
    """An observable condition that proves a task is done."""

    text: str
    source: str = "generated"


@dataclass
class TaskPackage:
    """A small unit of work suitable for an autonomous coding agent."""

    id: str
    title: str
    goal: str
    scope: List[str]
    input_files: List[str]
    acceptance_criteria: List[AcceptanceCriterion]
    risks: List[str]
    risk_score: int
    suggested_commands: List[str]
    dependencies: List[str]
    source_section: Optional[str] = None
    notes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SliceResult:
    """Full slicing output."""

    source: str
    tasks: List[TaskPackage]
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

