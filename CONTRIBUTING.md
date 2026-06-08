# Contributing

Thanks for improving `agent-task-slicer`.

## Development Setup

```bash
python -m pip install -e .
python -m unittest
```

The package targets Python 3.9+ and keeps runtime dependencies at zero. Please avoid adding non-standard-library runtime dependencies unless the project gains a very clear need.

## Heuristic Changes

Task recognition, dependency inference, risk scoring, and acceptance criteria generation are intentionally deterministic. When changing a heuristic:

- Add or update focused `unittest` coverage.
- Keep behavior explainable from the input text.
- Prefer conservative inference over surprising automation.
- Update README examples if user-facing output changes.

## Release Checklist

- `python -m unittest` passes.
- README English and Chinese sections are still accurate.
- `examples/sample_prd.md` still produces useful Markdown, JSON, and DOT.
- No real tokens, personal information, or network-only behavior were added.

