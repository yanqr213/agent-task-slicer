# Changelog

## 0.4.0 - 2026-06-09

- Added `parallel-plan`/`parallel`/`agent-plan` Markdown output for multi-agent execution waves.
- Added `parallel-json`/`dispatch-json` schema for orchestrators that need wave, slot, worktree, and prompt metadata.
- Added deterministic agent slots, suggested worktree branches/paths, dependency gap reporting, and per-task prompts.
- Expanded CLI, exporter tests, CI smoke checks, and Chinese/English documentation for parallel agent workflows.

## 0.3.0 - 2026-06-09

- Added `github-issues`/`gh-issues`/`issues` output for GitHub issue creation payloads.
- Added per-task issue titles, Markdown bodies, risk/area/dependency labels, assignee placeholders, and metadata.
- Updated README in Chinese and English with GitHub CLI import examples.
- Expanded tests and CI smoke checks for the new issue payload schema.

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
