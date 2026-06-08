"""Export task packages as Markdown, JSON and Graphviz DOT."""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from typing import Iterable, List

from .models import AcceptanceCriterion, SliceResult, TaskPackage


def export_result(result: SliceResult, fmt: str) -> str:
    """Export a result in ``markdown``, ``json`` or ``dot`` format."""

    normalized = normalize_format(fmt)
    if normalized == "markdown":
        return export_markdown(result)
    if normalized == "json":
        return export_json(result)
    if normalized == "dot":
        return export_dot(result)
    raise ValueError(f"unsupported format: {fmt}")


def normalize_format(fmt: str) -> str:
    value = fmt.lower().strip()
    aliases = {"md": "markdown", "markdown": "markdown", "json": "json", "dot": "dot", "graphviz": "dot"}
    if value not in aliases:
        raise ValueError(f"unsupported format: {fmt}")
    return aliases[value]


def export_markdown(result: SliceResult) -> str:
    lines = [
        "# Agent Task Slices",
        "",
        f"- Source: `{result.source}`",
        f"- Tasks: {len(result.tasks)}",
    ]
    if result.warnings:
        lines.append(f"- Warnings: {len(result.warnings)}")
    lines.append("")

    for task in result.tasks:
        lines.extend(_task_markdown(task))
        lines.append("")
    if result.warnings:
        lines.extend(["## Warnings", ""])
        lines.extend(f"- {warning}" for warning in result.warnings)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _task_markdown(task: TaskPackage) -> List[str]:
    lines = [
        f"## {task.id} {task.title}",
        "",
        f"**Goal:** {task.goal}",
        "",
        f"**Source section:** {task.source_section or 'N/A'}",
        "",
        "### Scope",
        "",
    ]
    lines.extend(_list_lines(task.scope))
    lines.extend(["", "### Input Files", ""])
    lines.extend(_list_lines(task.input_files))
    lines.extend(["", "### Acceptance Criteria", ""])
    lines.extend(_criteria_lines(task.acceptance_criteria))
    lines.extend(["", "### Risks", ""])
    lines.append(f"- Score: {task.risk_score}/5")
    lines.extend(_list_lines(task.risks))
    lines.extend(["", "### Suggested Verification", ""])
    lines.extend(f"- `{command}`" for command in task.suggested_commands)
    lines.extend(["", "### Dependencies", ""])
    lines.extend(_list_lines(task.dependencies))
    if task.notes:
        lines.extend(["", "### Notes", ""])
        lines.extend(_list_lines(task.notes))
    return lines


def _list_lines(items: Iterable[str]) -> List[str]:
    values = list(items)
    if not values:
        return ["- N/A"]
    return [f"- {item}" for item in values]


def _criteria_lines(criteria: Iterable[AcceptanceCriterion]) -> List[str]:
    values = list(criteria)
    if not values:
        return ["- N/A"]
    return [f"- [{criterion.source}] {criterion.text}" for criterion in values]


def export_json(result: SliceResult) -> str:
    payload = {
        "source": result.source,
        "warnings": result.warnings,
        "metadata": result.metadata,
        "tasks": [_task_to_json(task) for task in result.tasks],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _task_to_json(task: TaskPackage) -> dict:
    data = asdict(task)
    data["acceptance_criteria"] = [asdict(item) for item in task.acceptance_criteria]
    return data


def export_dot(result: SliceResult) -> str:
    lines = [
        "digraph agent_task_slices {",
        "  rankdir=LR;",
        '  node [shape=box, style="rounded,filled", fillcolor="#f7f7f7", fontname="Arial"];',
    ]
    for task in result.tasks:
        label = f"{task.id}\\n{_dot_escape(task.title)}\\nRisk {task.risk_score}/5"
        color = _risk_color(task.risk_score)
        lines.append(f'  "{_dot_escape(task.id)}" [label="{label}", fillcolor="{color}"];')
    for task in result.tasks:
        for dep in task.dependencies:
            lines.append(f'  "{_dot_escape(dep)}" -> "{_dot_escape(task.id)}";')
    lines.append("}")
    return "\n".join(lines) + "\n"


def _risk_color(score: int) -> str:
    if score >= 4:
        return "#ffe0e0"
    if score == 3:
        return "#fff0cc"
    return "#e8f5e9"


def _dot_escape(value: str) -> str:
    value = re.sub(r"\s+", " ", value)
    return value.replace("\\", "\\\\").replace('"', '\\"')

