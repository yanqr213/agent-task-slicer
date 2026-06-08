"""Markdown and plain text parsing."""

from __future__ import annotations

import os
import re
from typing import Iterable, List, Optional

from .errors import InputError
from .models import Document, DocumentSection

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
CHECKBOX_RE = re.compile(r"^\s*[-*+]\s+\[[ xX]\]\s+(.+?)\s*$")
BULLET_RE = re.compile(r"^\s*[-*+]\s+(.+?)\s*$")
ORDERED_RE = re.compile(r"^\s*\d+[.)]\s+(.+?)\s*$")
PATH_RE = re.compile(
    r"(?<![\w.-])((?:[A-Za-z]:[\\/])?(?:\.{1,2}[\\/])?(?:[\w.@+-]+[\\/])+[\w.@+-]+(?:\.[A-Za-z0-9]+)?)"
)
INLINE_CODE_PATH_RE = re.compile(r"`([^`\n]+[/\\][^`\n]+)`")


def parse_file(path: str) -> Document:
    """Parse a UTF-8 Markdown/plain text file."""

    if not os.path.exists(path):
        raise InputError(f"input file not found: {path}")
    if not os.path.isfile(path):
        raise InputError(f"input path is not a file: {path}")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except UnicodeDecodeError as exc:
        raise InputError(f"input file is not valid UTF-8: {path}") from exc
    except OSError as exc:
        raise InputError(f"cannot read input file: {path}") from exc
    return parse_text(text, source=path)


def parse_text(text: str, source: str = "<text>") -> Document:
    """Parse Markdown-ish text into sections.

    The parser is intentionally permissive: issue bodies, PRDs, checklists and
    copied chat transcripts often contain imperfect Markdown.
    """

    if not isinstance(text, str):
        raise InputError("input text must be a string")
    if not text.strip():
        raise InputError("input text is empty")

    lines = text.splitlines()
    title = _first_title(lines, source)
    heading_positions = _heading_positions(lines)
    sections = _build_sections(lines, heading_positions)
    if not sections:
        sections = [
            DocumentSection(
                title=title,
                level=1,
                content=text.strip(),
                start_line=1,
                end_line=max(1, len(lines)),
                path_hints=extract_paths(text),
                checklist_items=extract_checklist_items(text),
            )
        ]
    return Document(source=source, title=title, raw_text=text, sections=sections, path_hints=extract_paths(text))


def _first_title(lines: List[str], source: str) -> str:
    for line in lines:
        match = HEADING_RE.match(line)
        if match:
            return clean_text(match.group(2))
    basename = os.path.basename(source)
    return basename if basename and basename != "<text>" else "Untitled Request"


def _heading_positions(lines: List[str]) -> List[tuple]:
    positions = []
    for index, line in enumerate(lines):
        match = HEADING_RE.match(line)
        if match:
            positions.append((index, len(match.group(1)), clean_text(match.group(2))))
    return positions


def _build_sections(lines: List[str], heading_positions: List[tuple]) -> List[DocumentSection]:
    sections: List[DocumentSection] = []
    for pos_index, (line_index, level, title) in enumerate(heading_positions):
        next_line_index = heading_positions[pos_index + 1][0] if pos_index + 1 < len(heading_positions) else len(lines)
        content_lines = lines[line_index + 1 : next_line_index]
        content = "\n".join(content_lines).strip()
        section_text = "\n".join([title] + content_lines)
        sections.append(
            DocumentSection(
                title=title,
                level=level,
                content=content,
                start_line=line_index + 1,
                end_line=next_line_index,
                path_hints=extract_paths(section_text),
                checklist_items=extract_checklist_items(content),
            )
        )
    return sections


def clean_text(text: str) -> str:
    """Normalize Markdown-lite text for titles and criteria."""

    text = text.strip()
    text = re.sub(r"^#+\s*", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" -:\t")


def extract_checklist_items(text: str) -> List[str]:
    """Return checkbox items from Markdown text."""

    items = []
    for line in text.splitlines():
        match = CHECKBOX_RE.match(line)
        if match:
            items.append(clean_text(match.group(1)))
    return items


def extract_bullets(text: str) -> List[str]:
    """Return simple bullet and ordered-list items."""

    bullets = []
    for line in text.splitlines():
        checkbox = CHECKBOX_RE.match(line)
        if checkbox:
            bullets.append(clean_text(checkbox.group(1)))
            continue
        bullet = BULLET_RE.match(line)
        if bullet:
            bullets.append(clean_text(bullet.group(1)))
            continue
        ordered = ORDERED_RE.match(line)
        if ordered:
            bullets.append(clean_text(ordered.group(1)))
    return [item for item in bullets if item]


def extract_paths(text: str) -> List[str]:
    """Extract plausible file or directory paths."""

    text = re.sub(r"\bhttps?://\S+", " ", text)
    paths = []
    for match in INLINE_CODE_PATH_RE.finditer(text):
        paths.append(_normalize_path_hint(match.group(1)))
    for match in PATH_RE.finditer(text):
        paths.append(_normalize_path_hint(match.group(1)))
    return unique_preserve_order(path for path in paths if _looks_like_path(path))


def _normalize_path_hint(path: str) -> str:
    path = path.strip().strip(".,;:()[]{}<>\"'")
    return path.replace("\\", "/")


def _looks_like_path(path: str) -> bool:
    if "://" in path:
        return False
    if "/" not in path:
        return False
    if path.startswith("#"):
        return False
    return bool(re.search(r"[A-Za-z0-9_./-]", path))


def unique_preserve_order(items: Iterable[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            result.append(item)
            seen.add(item)
    return result
