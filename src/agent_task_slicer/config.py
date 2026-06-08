"""Configuration loading and validation."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from .errors import ConfigError


DEFAULT_RISK_KEYWORDS = {
    "security": 3,
    "auth": 3,
    "authentication": 3,
    "authorization": 3,
    "permission": 3,
    "migration": 3,
    "database": 3,
    "schema": 3,
    "payment": 3,
    "billing": 3,
    "external api": 2,
    "integration": 2,
    "concurrency": 2,
    "performance": 2,
    "cache": 2,
    "breaking": 2,
    "refactor": 2,
    "delete": 2,
    "remove": 2,
    "安全": 3,
    "鉴权": 3,
    "权限": 3,
    "迁移": 3,
    "数据库": 3,
    "支付": 3,
    "性能": 2,
    "缓存": 2,
    "重构": 2,
    "删除": 2,
}

DEFAULT_TASK_MARKERS = [
    "TODO",
    "Task",
    "Milestone",
    "Requirement",
    "Feature",
    "实现",
    "修复",
    "任务",
    "需求",
    "目标",
]


@dataclass(frozen=True)
class SlicerConfig:
    """Runtime settings for task slicing."""

    max_scope_items: int = 5
    min_task_words: int = 3
    max_tasks: int = 80
    default_test_commands: List[str] = field(default_factory=lambda: ["python -m unittest"])
    risk_keywords: Dict[str, int] = field(default_factory=lambda: dict(DEFAULT_RISK_KEYWORDS))
    task_markers: List[str] = field(default_factory=lambda: list(DEFAULT_TASK_MARKERS))
    path_roots: List[str] = field(default_factory=lambda: ["src", "tests", "docs", "examples", "scripts", ".github"])
    package_prefix: str = "T"
    infer_dependencies: bool = True
    include_low_confidence_tasks: bool = True


def _ensure_int(name: str, value: Any, minimum: int, maximum: Optional[int] = None) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ConfigError(f"{name} must be an integer")
    if value < minimum:
        raise ConfigError(f"{name} must be >= {minimum}")
    if maximum is not None and value > maximum:
        raise ConfigError(f"{name} must be <= {maximum}")
    return value


def _ensure_bool(name: str, value: Any) -> bool:
    if not isinstance(value, bool):
        raise ConfigError(f"{name} must be a boolean")
    return value


def _ensure_string_list(name: str, value: Any) -> List[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigError(f"{name} must be a list of strings")
    return [item for item in value if item.strip()]


def _ensure_risk_keywords(value: Any) -> Dict[str, int]:
    if not isinstance(value, dict):
        raise ConfigError("risk_keywords must be an object")
    result: Dict[str, int] = {}
    for key, score in value.items():
        if not isinstance(key, str) or not key.strip():
            raise ConfigError("risk_keywords keys must be non-empty strings")
        if not isinstance(score, int) or isinstance(score, bool) or score < 1 or score > 5:
            raise ConfigError("risk_keywords values must be integers from 1 to 5")
        result[key] = score
    return result


def validate_config(data: Dict[str, Any]) -> SlicerConfig:
    """Validate a config mapping and return a typed config."""

    if not isinstance(data, dict):
        raise ConfigError("config must be a JSON object")

    allowed = set(SlicerConfig.__dataclass_fields__.keys())
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise ConfigError(f"unknown config keys: {', '.join(unknown)}")

    base = SlicerConfig()
    values = {
        "max_scope_items": base.max_scope_items,
        "min_task_words": base.min_task_words,
        "max_tasks": base.max_tasks,
        "default_test_commands": list(base.default_test_commands),
        "risk_keywords": dict(base.risk_keywords),
        "task_markers": list(base.task_markers),
        "path_roots": list(base.path_roots),
        "package_prefix": base.package_prefix,
        "infer_dependencies": base.infer_dependencies,
        "include_low_confidence_tasks": base.include_low_confidence_tasks,
    }
    values.update(data)

    return SlicerConfig(
        max_scope_items=_ensure_int("max_scope_items", values["max_scope_items"], 1, 20),
        min_task_words=_ensure_int("min_task_words", values["min_task_words"], 1, 100),
        max_tasks=_ensure_int("max_tasks", values["max_tasks"], 1, 500),
        default_test_commands=_ensure_string_list("default_test_commands", values["default_test_commands"]),
        risk_keywords=_ensure_risk_keywords(values["risk_keywords"]),
        task_markers=_ensure_string_list("task_markers", values["task_markers"]),
        path_roots=_ensure_string_list("path_roots", values["path_roots"]),
        package_prefix=_validate_prefix(values["package_prefix"]),
        infer_dependencies=_ensure_bool("infer_dependencies", values["infer_dependencies"]),
        include_low_confidence_tasks=_ensure_bool(
            "include_low_confidence_tasks", values["include_low_confidence_tasks"]
        ),
    )


def _validate_prefix(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError("package_prefix must be a non-empty string")
    if any(ch.isspace() for ch in value):
        raise ConfigError("package_prefix must not contain whitespace")
    return value


def load_config(path: Optional[str] = None, overrides: Optional[Dict[str, Any]] = None) -> SlicerConfig:
    """Load config from JSON and apply optional overrides.

    When ``path`` is omitted, the defaults are returned. The file format is
    intentionally JSON so the project stays dependency-free on Python 3.9.
    """

    data: Dict[str, Any] = {}
    if path:
        if not os.path.exists(path):
            raise ConfigError(f"config file not found: {path}")
        try:
            with open(path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ConfigError(f"invalid JSON config: {exc}") from exc
        data.update(loaded)
    if overrides:
        data.update(overrides)
    return validate_config(data)


def merge_config_fragments(fragments: Iterable[Dict[str, Any]]) -> SlicerConfig:
    """Merge several config fragments, later fragments winning."""

    merged: Dict[str, Any] = {}
    for fragment in fragments:
        merged.update(fragment)
    return validate_config(merged)

