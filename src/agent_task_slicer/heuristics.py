"""Heuristics for identifying and enriching task packages."""

from __future__ import annotations

import re
from typing import Iterable, List, Sequence

from .config import SlicerConfig
from .models import AcceptanceCriterion, Document, DocumentSection, TaskPackage
from .parser import clean_text, extract_bullets, extract_paths, unique_preserve_order

ACTION_RE = re.compile(
    r"\b(add|build|create|implement|support|fix|refactor|migrate|remove|document|test|validate|export|parse|read|write|"
    r"生成|实现|支持|修复|重构|迁移|删除|文档|测试|校验|导出|解析|读取|写入)\b",
    re.IGNORECASE,
)
DEPENDENCY_RE = re.compile(
    r"(?:depends on|after|requires|blocked by|依赖|前置|之后|完成后)\s*[:：]?\s*([^\n。；;]+)",
    re.IGNORECASE,
)
TEST_HINT_RE = re.compile(r"\b(test|unittest|pytest|lint|mypy|ruff|npm test|go test|cargo test|测试|验证)\b", re.I)


def identify_tasks(document: Document, config: SlicerConfig) -> List[TaskPackage]:
    """Identify candidate tasks from sections and lists."""

    candidates = []
    for section in document.sections:
        section_tasks = _tasks_from_section(section, document, config)
        candidates.extend(section_tasks)

    if not candidates:
        candidates.extend(_tasks_from_bullets(document, config))

    if not candidates and config.include_low_confidence_tasks:
        candidates.append(_fallback_task(document, config))

    limited = candidates[: config.max_tasks]
    for index, task in enumerate(limited, start=1):
        task.id = f"{config.package_prefix}{index:03d}"
    return limited


def enrich_tasks(tasks: List[TaskPackage], document: Document, config: SlicerConfig) -> List[TaskPackage]:
    """Add dependencies, risk and validation hints."""

    for task in tasks:
        task.input_files = unique_preserve_order(task.input_files or _infer_files_for_task(task, document, config))
        task.risks = risk_reasons(task, config)
        task.risk_score = risk_score(task, config)
        if not task.acceptance_criteria:
            task.acceptance_criteria = generated_acceptance_criteria(task)
        task.suggested_commands = suggested_commands(task, config)

    if config.infer_dependencies:
        infer_dependencies(tasks)
    return tasks


def _tasks_from_section(section: DocumentSection, document: Document, config: SlicerConfig) -> List[TaskPackage]:
    text = "\n".join([section.title, section.content])
    bullets = extract_bullets(section.content)
    actionable_bullets = [item for item in bullets if _is_task_like(item, config)]

    tasks: List[TaskPackage] = []
    if _is_task_like(section.title, config):
        task_title = _make_title(section.title, actionable_bullets)
        scope = actionable_bullets[: config.max_scope_items] or _scope_from_text(section.content, config)
        tasks.append(
            TaskPackage(
                id="",
                title=task_title,
                goal=_goal_from_title(task_title),
                scope=scope,
                input_files=unique_preserve_order(section.path_hints or _infer_files_from_text(text, document, config)),
                acceptance_criteria=_criteria_from_text(section.content),
                risks=[],
                risk_score=1,
                suggested_commands=[],
                dependencies=[],
                source_section=section.title,
                notes=_notes_from_section(section),
                metadata={
                    "start_line": section.start_line,
                    "end_line": section.end_line,
                    "dependency_refs": _explicit_dependencies(text),
                },
            )
        )
        return tasks

    if actionable_bullets:
        for bullet in actionable_bullets:
            tasks.append(_task_from_line(bullet, section, document, config))
        return tasks

    if len(bullets) >= 2 and section.level <= 3:
        for bullet in bullets:
            if _word_count(bullet) >= config.min_task_words:
                tasks.append(_task_from_line(bullet, section, document, config))
    return tasks


def _tasks_from_bullets(document: Document, config: SlicerConfig) -> List[TaskPackage]:
    tasks = []
    for section in document.sections:
        for bullet in extract_bullets(section.content):
            if _is_task_like(bullet, config):
                tasks.append(_task_from_line(bullet, section, document, config))
    return tasks


def _task_from_line(line: str, section: DocumentSection, document: Document, config: SlicerConfig) -> TaskPackage:
    title = _title_from_line(line)
    return TaskPackage(
        id="",
        title=title,
        goal=_goal_from_title(title),
        scope=[clean_text(line)],
        input_files=unique_preserve_order(extract_paths(line) or section.path_hints or _infer_files_from_text(line, document, config)),
        acceptance_criteria=_criteria_from_text(line),
        risks=[],
        risk_score=1,
        suggested_commands=[],
        dependencies=[],
        source_section=section.title,
        metadata={
            "start_line": section.start_line,
            "end_line": section.end_line,
            "dependency_refs": _explicit_dependencies(line),
        },
    )


def _fallback_task(document: Document, config: SlicerConfig) -> TaskPackage:
    title = f"梳理并实现：{document.title}"
    scope = _scope_from_text(document.raw_text, config) or ["阅读输入需求，拆分可执行修改并完成最小可验收实现"]
    return TaskPackage(
        id="",
        title=title,
        goal=_goal_from_title(title),
        scope=scope,
        input_files=document.path_hints,
        acceptance_criteria=[],
        risks=[],
        risk_score=1,
        suggested_commands=[],
        dependencies=[],
        source_section=document.title,
        notes=["低置信度任务：输入缺少明确任务标记，已按整体需求生成。"],
    )


def _is_task_like(text: str, config: SlicerConfig) -> bool:
    normalized = text.strip()
    if _word_count(normalized) < config.min_task_words:
        return False
    lower = normalized.lower()
    if any(marker.lower() in lower for marker in config.task_markers):
        return True
    return bool(ACTION_RE.search(normalized))


def _word_count(text: str) -> int:
    latin = re.findall(r"[A-Za-z0-9_]+", text)
    cjk = re.findall(r"[\u4e00-\u9fff]", text)
    return len(latin) + max(1 if cjk else 0, len(cjk) // 2)


def _make_title(section_title: str, bullets: Sequence[str]) -> str:
    title = clean_text(section_title)
    if title and title.lower() not in {"todo", "tasks", "任务", "需求"}:
        return _title_from_line(title)
    if bullets:
        return _title_from_line(bullets[0])
    return title or "未命名任务"


def _title_from_line(line: str) -> str:
    line = clean_text(re.sub(r"^\[[ xX]\]\s*", "", line))
    line = re.sub(r"^(TODO|Task|任务|需求|目标)\s*[:：-]\s*", "", line, flags=re.I)
    if len(line) <= 72:
        return line
    return line[:69].rstrip() + "..."


def _goal_from_title(title: str) -> str:
    title = clean_text(title)
    if re.search(r"[\u4e00-\u9fff]", title):
        return f"完成“{title}”，交付可验证、边界清晰的代码或文档变更。"
    return f"Complete '{title}' with a verifiable, scoped change."


def _scope_from_text(text: str, config: SlicerConfig) -> List[str]:
    bullets = extract_bullets(text)
    if bullets:
        return bullets[: config.max_scope_items]
    sentences = re.split(r"(?<=[。.!?])\s+", text.strip())
    return [clean_text(sentence) for sentence in sentences if clean_text(sentence)][: config.max_scope_items]


def _criteria_from_text(text: str) -> List[AcceptanceCriterion]:
    criteria = []
    for line in extract_bullets(text):
        lower = line.lower()
        if any(key in lower for key in ["accept", "验收", "done", "完成", "should", "must", "必须"]):
            criteria.append(AcceptanceCriterion(text=_criterion_text(line), source="input"))
    return criteria


def _criterion_text(text: str) -> str:
    text = clean_text(text)
    if text.endswith(("。", ".", "！", "!")):
        return text
    return text + "。"


def generated_acceptance_criteria(task: TaskPackage) -> List[AcceptanceCriterion]:
    criteria = [
        AcceptanceCriterion(
            text=f"任务目标“{task.title}”已实现，且变更范围与工作包 scope 保持一致。",
            source="generated",
        ),
        AcceptanceCriterion(
            text="相关输入文件或模块已更新，并保留现有公开接口的兼容性，除非任务明确要求破坏性变更。",
            source="generated",
        ),
        AcceptanceCriterion(
            text="建议验证命令能够通过，或已在任务记录中说明无法执行的原因。",
            source="generated",
        ),
    ]
    if task.input_files:
        criteria.append(
            AcceptanceCriterion(
                text=f"已检查关键路径：{', '.join(task.input_files[:3])}。",
                source="generated",
            )
        )
    return criteria


def _notes_from_section(section: DocumentSection) -> List[str]:
    notes = []
    if section.checklist_items:
        notes.append(f"来自 checklist：{len(section.checklist_items)} 项。")
    return notes


def _infer_files_for_task(task: TaskPackage, document: Document, config: SlicerConfig) -> List[str]:
    text = "\n".join([task.title, task.goal] + task.scope)
    return _infer_files_from_text(text, document, config)


def _infer_files_from_text(text: str, document: Document, config: SlicerConfig) -> List[str]:
    paths = extract_paths(text)
    if paths:
        return paths

    inferred = []
    lower = text.lower()
    if any(key in lower for key in ["test", "测试", "验收", "验证"]):
        inferred.append("tests/")
    if any(key in lower for key in ["doc", "readme", "文档"]):
        inferred.append("docs/")
    if any(key in lower for key in ["cli", "command", "命令行"]):
        inferred.append("src/")
    if not inferred:
        for root in config.path_roots:
            if root.lower() in lower:
                inferred.append(root.rstrip("/") + "/")
    if not inferred and document.path_hints:
        inferred.extend(document.path_hints[:3])
    return unique_preserve_order(inferred)


def risk_score(task: TaskPackage, config: SlicerConfig) -> int:
    """Return a 1-5 risk score."""

    text = _task_text(task).lower()
    score = 1
    for keyword, weight in config.risk_keywords.items():
        if keyword.lower() in text:
            score += weight
    if len(task.input_files) > 4:
        score += 1
    if len(task.scope) > 4:
        score += 1
    if not task.input_files:
        score += 1
    return max(1, min(5, score))


def risk_reasons(task: TaskPackage, config: SlicerConfig) -> List[str]:
    text = _task_text(task).lower()
    reasons = []
    for keyword, weight in config.risk_keywords.items():
        if keyword.lower() in text:
            reasons.append(f"命中风险关键词“{keyword}”（权重 {weight}）。")
    if len(task.input_files) > 4:
        reasons.append("涉及文件较多，可能需要额外回归。")
    if len(task.scope) > 4:
        reasons.append("scope 项较多，建议执行时继续拆小。")
    if not task.input_files:
        reasons.append("缺少明确输入文件，agent 需要先定位代码。")
    return unique_preserve_order(reasons) or ["常规实现风险。"]


def _task_text(task: TaskPackage) -> str:
    return "\n".join([task.title, task.goal] + task.scope + task.input_files)


def suggested_commands(task: TaskPackage, config: SlicerConfig) -> List[str]:
    commands = []
    text = _task_text(task)
    if TEST_HINT_RE.search(text):
        commands.extend(config.default_test_commands)
    if any(path.startswith("tests") or "/tests/" in path for path in task.input_files):
        commands.extend(config.default_test_commands)
    if any(path.endswith(".py") or path.startswith("src") for path in task.input_files):
        commands.extend(config.default_test_commands)
    if any("README" in path or path.startswith("docs") for path in task.input_files):
        commands.append("python -m unittest")
    if not commands:
        commands.extend(config.default_test_commands)
    return unique_preserve_order(commands)


def infer_dependencies(tasks: List[TaskPackage]) -> None:
    """Infer dependencies in-place using explicit references and shared paths."""

    id_by_title = {task.title.lower(): task.id for task in tasks}
    for index, task in enumerate(tasks):
        deps = list(task.dependencies)
        deps.extend(_dependencies_from_references(task, tasks, id_by_title))
        deps.extend(_dependencies_from_shared_paths(index, task, tasks))
        task.dependencies = [dep for dep in unique_preserve_order(deps) if dep != task.id]


def _dependencies_from_references(task: TaskPackage, tasks: List[TaskPackage], id_by_title: dict) -> List[str]:
    text = "\n".join([task.title] + task.scope + task.notes)
    refs = list(task.metadata.get("dependency_refs", []))
    refs.extend(_explicit_dependencies(text))
    deps = []
    for ref in refs:
        normalized = ref.strip().lower().lstrip("#")
        if normalized in id_by_title:
            deps.append(id_by_title[normalized])
            continue
        for other in tasks:
            if normalized == other.id.lower() or normalized in other.title.lower():
                deps.append(other.id)
    return deps


def _explicit_dependencies(text: str) -> List[str]:
    deps = []
    for match in DEPENDENCY_RE.finditer(text):
        raw = match.group(1)
        for part in re.split(r"[,，、;；]", raw):
            value = clean_text(part)
            if value:
                deps.append(value)
    return unique_preserve_order(deps)


def _dependencies_from_shared_paths(index: int, task: TaskPackage, tasks: List[TaskPackage]) -> List[str]:
    deps = []
    current_paths = set(task.input_files)
    if not current_paths:
        return deps
    for previous in tasks[:index]:
        if current_paths.intersection(previous.input_files):
            deps.append(previous.id)
    return deps
