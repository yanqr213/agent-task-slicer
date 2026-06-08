"""Command line interface."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Iterable, Optional

from . import __version__
from .config import load_config
from .errors import (
    ConfigError,
    ExportError,
    InputError,
    SlicerError,
    EXIT_CONFIG_ERROR,
    EXIT_EXPORT_ERROR,
    EXIT_INPUT_ERROR,
    EXIT_INTERNAL_ERROR,
    EXIT_NO_TASKS,
    EXIT_OK,
)
from .exporters import export_result, normalize_format
from .slicer import TaskSlicer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-task-slicer",
        description="Slice Markdown/issue/PRD/task text into agent-ready work packages.",
    )
    parser.add_argument("input", nargs="?", help="Input Markdown/text file. Use '-' to read stdin.")
    parser.add_argument(
        "-f",
        "--format",
        default="markdown",
        choices=[
            "markdown",
            "md",
            "json",
            "jsonl",
            "ndjson",
            "queue",
            "prompt",
            "prompts",
            "prompt-pack",
            "agent-prompts",
            "dot",
            "graphviz",
        ],
        help="Output format. Use prompt-pack or jsonl to hand tasks directly to coding agents.",
    )
    parser.add_argument("-o", "--output", help="Output file. Defaults to stdout.")
    parser.add_argument("-c", "--config", help="JSON config file.")
    parser.add_argument("--max-tasks", type=int, help="Override maximum number of tasks.")
    parser.add_argument("--prefix", help="Override package id prefix, e.g. A or TASK.")
    parser.add_argument("--no-deps", action="store_true", help="Disable dependency inference.")
    parser.add_argument("--fail-on-empty", action="store_true", help="Exit with code 4 when no tasks are produced.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        fmt = normalize_format(args.format)
        config = _load_cli_config(args)
        text = _read_input(args.input)
        result = TaskSlicer(config).slice_text(text, source=args.input or "<stdin>")
        if args.fail_on_empty and not result.tasks:
            _write_stderr("no tasks produced")
            return EXIT_NO_TASKS
        output = export_result(result, fmt)
        _write_output(output, args.output)
        return EXIT_OK
    except ConfigError as exc:
        _write_stderr(str(exc))
        return EXIT_CONFIG_ERROR
    except InputError as exc:
        _write_stderr(str(exc))
        return EXIT_INPUT_ERROR
    except ExportError as exc:
        _write_stderr(str(exc))
        return EXIT_EXPORT_ERROR
    except SlicerError as exc:
        _write_stderr(str(exc))
        return EXIT_INTERNAL_ERROR
    except ValueError as exc:
        _write_stderr(str(exc))
        return EXIT_CONFIG_ERROR


def _load_cli_config(args: argparse.Namespace):
    overrides = {}
    if args.max_tasks is not None:
        overrides["max_tasks"] = args.max_tasks
    if args.prefix is not None:
        overrides["package_prefix"] = args.prefix
    if args.no_deps:
        overrides["infer_dependencies"] = False
    return load_config(args.config, overrides=overrides)


def _read_input(path: Optional[str]) -> str:
    if not path or path == "-":
        data = sys.stdin.read()
        if not data.strip():
            raise InputError("stdin is empty")
        return data
    if not os.path.exists(path):
        raise InputError(f"input file not found: {path}")
    if not os.path.isfile(path):
        raise InputError(f"input path is not a file: {path}")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = handle.read()
    except UnicodeDecodeError as exc:
        raise InputError(f"input file is not valid UTF-8: {path}") from exc
    except OSError as exc:
        raise InputError(f"cannot read input file: {path}") from exc
    if not data.strip():
        raise InputError("input file is empty")
    return data


def _write_output(text: str, path: Optional[str]) -> None:
    if not path:
        sys.stdout.write(text)
        return
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    except OSError as exc:
        raise ExportError(f"cannot write output file: {path}") from exc


def _write_stderr(message: str) -> None:
    sys.stderr.write(f"agent-task-slicer: {message}\n")
