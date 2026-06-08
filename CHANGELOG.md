# Changelog

## 0.2.0 - 2026-06-09

- Added `prompt-pack` output for copy-paste-ready Codex/Claude Code/internal agent prompts.
- Added `jsonl`/`ndjson`/`queue` output with one structured agent queue item per line.
- Added deterministic per-task prompt generation in the Python API.
- Updated CI smoke tests to cover the new agent handoff formats.
- Updated GitHub Actions to `actions/checkout@v5` and `actions/setup-python@v6`.

## 0.1.0

- Initial open source project scaffold.
- Added Markdown/plain text parsing.
- Added task identification, dependency inference, risk scoring, acceptance criteria generation, and verification command suggestions.
- Added Markdown, JSON, and Graphviz DOT exporters.
- Added CLI, importable Python API, examples, config validation, tests, and GitHub Actions CI.
