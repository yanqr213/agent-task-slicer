"""Export task packages as Markdown, JSON, JSONL, prompt packs, GitHub issues and DOT."""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from typing import Iterable, List

from .models import AcceptanceCriterion, SliceResult, TaskPackage


def export_result(result: SliceResult, fmt: str) -> str:
    """Export a result in a supported report or agent handoff format."""

    normalized = normalize_format(fmt)
    if normalized == "markdown":
        return export_markdown(result)
    if normalized == "json":
        return export_json(result)
    if normalized == "jsonl":
        return export_jsonl(result)
    if normalized == "prompt-pack":
        return export_prompt_pack(result)
    if normalized == "github-issues":
        return export_github_issues(result)
    if normalized == "dot":
        return export_dot(result)
    raise ValueError(f"unsupported format: {fmt}")


def normalize_format(fmt: str) -> str:
    value = fmt.lower().strip()
    aliases = {
        "md": "markdown",
        "markdown": "markdown",
        "json": "json",
        "jsonl": "jsonl",
        "ndjson": "jsonl",
        "queue": "jsonl",
        "prompt": "prompt-pack",
        "prompts": "prompt-pack",
        "prompt-pack": "prompt-pack",
        "agent-prompts": "prompt-pack",
        "github-issues": "github-issues",
        "gh-issues": "github-issues",
        "issues": "github-issues",
        "dot": "dot",
        "graphviz": "dot",
    }
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


def export_jsonl(result: SliceResult) -> str:
    """Export one runnable agent queue item per line."""

    lines = []
    for index, task in enumerate(result.tasks, start=1):
        payload = {
            "schema": "agent-task-slicer.queue.v1",
            "sequence": index,
            "source": result.source,
            "task": _task_to_json(task),
            "prompt": build_agent_prompt(task, result),
        }
        lines.append(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return "\n".join(lines) + ("\n" if lines else "")


def export_prompt_pack(result: SliceResult) -> str:
    """Export copy-paste-ready prompts for coding agents."""

    lines = [
        "# Agent Prompt Pack",
        "",
        f"- Source: `{result.source}`",
        f"- Tasks: {len(result.tasks)}",
        "- Format: one fenced prompt per task",
        "",
    ]
    if result.warnings:
        lines.append(f"- Warnings: {len(result.warnings)}")
        lines.append("")
    for task in result.tasks:
        lines.extend([
            f"## {task.id} {task.title}",
            "",
            "```text",
            build_agent_prompt(task, result).rstrip(),
            "```",
            "",
        ])
    if result.warnings:
        lines.extend(["## Warnings", ""])
        lines.extend(f"- {warning}" for warning in result.warnings)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def export_github_issues(result: SliceResult) -> str:
    """Export GitHub issue creation payloads for each task package."""

    payload = {
        "schema": "agent-task-slicer.github-issues.v1",
        "source": result.source,
        "metadata": result.metadata,
        "warnings": result.warnings,
        "issues": [_task_to_github_issue(task, result, index) for index, task in enumerate(result.tasks, start=1)],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _task_to_github_issue(task: TaskPackage, result: SliceResult, sequence: int) -> dict:
    return {
        "sequence": sequence,
        "task_id": task.id,
        "title": _github_issue_title(task),
        "body": _github_issue_body(task, result),
        "labels": _github_issue_labels(task),
        "assignees": [],
        "metadata": {
            "source": result.source,
            "source_section": task.source_section,
            "risk_score": task.risk_score,
            "dependencies": task.dependencies,
        },
    }


def _github_issue_title(task: TaskPackage) -> str:
    title = f"[{task.id}] {task.title}".strip()
    if len(title) <= 120:
        return title
    return title[:117].rstrip() + "..."


def _github_issue_body(task: TaskPackage, result: SliceResult) -> str:
    lines = [
        "<!-- Generated by agent-task-slicer. Review labels, assignees and scope before creating the issue. -->",
        "",
        "## Goal",
        "",
        task.goal,
        "",
        "## Source",
        "",
        f"- Source: `{result.source}`",
        f"- Task ID: `{task.id}`",
        f"- Source section: {task.source_section or 'N/A'}",
        f"- Risk: {task.risk_score}/5",
        "",
        "## Scope",
        "",
    ]
    lines.extend(_list_lines(task.scope))
    lines.extend(["", "## Input Files", ""])
    lines.extend(_list_lines(task.input_files))
    lines.extend(["", "## Acceptance Criteria", ""])
    lines.extend(_criteria_checkbox_lines(task.acceptance_criteria))
    lines.extend(["", "## Suggested Verification", ""])
    lines.extend(_command_checkbox_lines(task.suggested_commands))
    lines.extend(["", "## Dependencies", ""])
    lines.extend(_list_lines(task.dependencies))
    lines.extend([
        "",
        "## Agent Prompt",
        "",
        "```text",
        build_agent_prompt(task, result).rstrip(),
        "```",
        "",
    ])
    return "\n".join(lines).rstrip() + "\n"


def _criteria_checkbox_lines(criteria: Iterable[AcceptanceCriterion]) -> List[str]:
    values = list(criteria)
    if not values:
        return ["- [ ] N/A"]
    return [f"- [ ] [{criterion.source}] {criterion.text}" for criterion in values]


def _command_checkbox_lines(commands: Iterable[str]) -> List[str]:
    values = list(commands)
    if not values:
        return ["- [ ] N/A"]
    return [f"- [ ] `{command}`" for command in values]


def _github_issue_labels(task: TaskPackage) -> List[str]:
    labels = ["agent-task", _risk_label(task.risk_score)]
    area = _area_label(task)
    if area:
        labels.append(area)
    if task.dependencies:
        labels.append("has-dependencies")
    return labels


def _risk_label(score: int) -> str:
    if score >= 4:
        return "risk:high"
    if score == 3:
        return "risk:medium"
    return "risk:low"


def _area_label(task: TaskPackage) -> str:
    for path in task.input_files:
        root = _path_root(path)
        if root:
            return f"area:{_label_slug(root)}"
    return ""


def _path_root(path: str) -> str:
    cleaned = path.strip().strip("`").strip()
    if not cleaned:
        return ""
    return re.split(r"[\\/]", cleaned, maxsplit=1)[0].strip(".")


def _label_slug(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip().lower())
    value = value.strip("-._")
    return value or "general"


def build_agent_prompt(task: TaskPackage, result: SliceResult) -> str:
    """Build a deterministic prompt for one task package."""

    lines = [
        f"You are working on task {task.id}: {task.title}",
        "",
        "Goal:",
        task.goal,
        "",
        f"Source: {result.source}",
    ]
    if task.source_section:
        lines.append(f"Source section: {task.source_section}")
    lines.extend(["", "Scope:"])
    lines.extend(_list_lines(task.scope))
    lines.extend(["", "Input files or paths:"])
    lines.extend(_list_lines(task.input_files))
    lines.extend(["", "Acceptance criteria:"])
    lines.extend(_criteria_lines(task.acceptance_criteria))
    lines.extend(["", "Risk notes:"])
    lines.append(f"- Risk score: {task.risk_score}/5")
    lines.extend(_list_lines(task.risks))
    lines.extend(["", "Suggested verification commands:"])
    lines.extend(f"- `{command}`" for command in task.suggested_commands)
    lines.extend(["", "Dependencies:"])
    lines.extend(_list_lines(task.dependencies))
    lines.extend([
        "",
        "Operating rules:",
        "- Keep the change scoped to this task unless a dependency explicitly requires broader work.",
        "- Preserve unrelated user or repository changes.",
        "- Run the suggested verification commands when possible.",
        "- Report changed files, verification results, remaining risks, and follow-up tasks.",
    ])
    return "\n".join(lines) + "\n"


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
