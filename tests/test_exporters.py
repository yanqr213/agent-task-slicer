import json
import unittest

from agent_task_slicer.exporters import (
    build_agent_prompt,
    export_dot,
    export_json,
    export_jsonl,
    export_markdown,
    export_prompt_pack,
    export_result,
    normalize_format,
)
from agent_task_slicer.slicer import slice_text


TEXT = """# X
## Task: build parser
- Implement `src/parser.py`.
## Task: test parser
- Add tests for `src/parser.py`.
"""


class ExporterTests(unittest.TestCase):
    def setUp(self):
        self.result = slice_text(TEXT)

    def test_normalize_format_aliases(self):
        self.assertEqual(normalize_format("md"), "markdown")
        self.assertEqual(normalize_format("graphviz"), "dot")
        self.assertEqual(normalize_format("ndjson"), "jsonl")
        self.assertEqual(normalize_format("agent-prompts"), "prompt-pack")

    def test_normalize_format_rejects_unknown(self):
        with self.assertRaises(ValueError):
            normalize_format("xml")

    def test_export_result_dispatches_markdown(self):
        output = export_result(self.result, "markdown")
        self.assertIn("# Agent Task Slices", output)

    def test_export_result_dispatches_json(self):
        output = export_result(self.result, "json")
        self.assertIn('"tasks"', output)

    def test_export_result_dispatches_dot(self):
        output = export_result(self.result, "dot")
        self.assertTrue(output.startswith("digraph"))

    def test_export_result_dispatches_jsonl(self):
        output = export_result(self.result, "jsonl")
        first = json.loads(output.splitlines()[0])
        self.assertEqual(first["schema"], "agent-task-slicer.queue.v1")

    def test_export_result_dispatches_prompt_pack(self):
        output = export_result(self.result, "prompt-pack")
        self.assertIn("# Agent Prompt Pack", output)
        self.assertIn("Operating rules:", output)

    def test_export_result_rejects_unknown(self):
        with self.assertRaises(ValueError):
            export_result(self.result, "bad")

    def test_markdown_contains_task_sections(self):
        output = export_markdown(self.result)
        self.assertIn("## T001", output)
        self.assertIn("### Acceptance Criteria", output)
        self.assertIn("### Suggested Verification", output)

    def test_markdown_uses_na_for_missing_dependencies(self):
        output = export_markdown(self.result)
        self.assertIn("- N/A", output)

    def test_json_is_parseable(self):
        payload = json.loads(export_json(self.result))
        self.assertEqual(payload["source"], "<text>")
        self.assertEqual(len(payload["tasks"]), 2)

    def test_json_contains_acceptance_criteria_objects(self):
        payload = json.loads(export_json(self.result))
        criterion = payload["tasks"][0]["acceptance_criteria"][0]
        self.assertIn("text", criterion)
        self.assertIn("source", criterion)

    def test_jsonl_contains_one_queue_item_per_task(self):
        rows = [json.loads(line) for line in export_jsonl(self.result).splitlines()]
        self.assertEqual(len(rows), len(self.result.tasks))
        self.assertEqual(rows[0]["task"]["id"], "T001")
        self.assertIn("Suggested verification commands:", rows[0]["prompt"])

    def test_prompt_pack_contains_copy_paste_prompts(self):
        output = export_prompt_pack(self.result)
        self.assertIn("```text", output)
        self.assertIn("You are working on task T001", output)
        self.assertIn("Report changed files", output)

    def test_build_agent_prompt_mentions_dependencies(self):
        prompt = build_agent_prompt(self.result.tasks[1], self.result)
        self.assertIn("Dependencies:", prompt)
        self.assertIn("T001", prompt)

    def test_dot_contains_nodes_and_edges(self):
        output = export_dot(self.result)
        self.assertIn('"T001"', output)
        self.assertIn('"T001" -> "T002"', output)

    def test_dot_escapes_quotes(self):
        result = slice_text('# X\n## Task: build "quoted" parser\n- Implement `src/parser.py`.')
        output = export_dot(result)
        self.assertIn('\\"quoted\\"', output)

    def test_dot_colors_high_risk(self):
        result = slice_text("# X\n## Task: implement auth database migration\n- Change `src/auth.py`.")
        output = export_dot(result)
        self.assertIn("#ffe0e0", output)


if __name__ == "__main__":
    unittest.main()
