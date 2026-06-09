import json
import unittest

from agent_task_slicer.models import SliceResult
from agent_task_slicer.exporters import (
    build_agent_prompt,
    export_dot,
    export_github_issues,
    export_json,
    export_jsonl,
    export_markdown,
    export_parallel_json,
    export_parallel_plan,
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
        self.assertEqual(normalize_format("parallel"), "parallel-plan")
        self.assertEqual(normalize_format("agent-plan"), "parallel-plan")
        self.assertEqual(normalize_format("dispatch-json"), "parallel-json")
        self.assertEqual(normalize_format("gh-issues"), "github-issues")
        self.assertEqual(normalize_format("issues"), "github-issues")

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

    def test_export_result_dispatches_github_issues(self):
        output = export_result(self.result, "github-issues")
        payload = json.loads(output)
        self.assertEqual(payload["schema"], "agent-task-slicer.github-issues.v1")

    def test_export_result_dispatches_parallel_plan(self):
        output = export_result(self.result, "parallel-plan")
        self.assertIn("# Agent Parallel Execution Plan", output)
        self.assertIn("## Wave 1", output)

    def test_export_result_dispatches_parallel_json(self):
        output = export_result(self.result, "parallel-json")
        payload = json.loads(output)
        self.assertEqual(payload["schema"], "agent-task-slicer.parallel-plan.v1")

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

    def test_parallel_json_groups_tasks_by_dependency_waves(self):
        payload = json.loads(export_parallel_json(self.result))

        self.assertEqual(payload["summary"]["tasks"], 2)
        self.assertEqual(payload["summary"]["waves"], 2)
        self.assertEqual(payload["waves"][0]["tasks"][0]["task_id"], "T001")
        self.assertEqual(payload["waves"][1]["tasks"][0]["dependencies"], ["T001"])
        self.assertEqual(payload["waves"][0]["tasks"][0]["agent_slot"], "agent-01-01")
        self.assertTrue(payload["waves"][0]["tasks"][0]["worktree_branch"].startswith("agent/t001-"))
        self.assertIn("You are working on task T001", payload["waves"][0]["tasks"][0]["prompt"])

    def test_parallel_plan_contains_worktree_and_prompts(self):
        output = export_parallel_plan(self.result)

        self.assertIn("Max parallel tasks:", output)
        self.assertIn("Worktree Branch", output)
        self.assertIn("agent-01-01", output)
        self.assertIn("```text", output)

    def test_parallel_json_reports_missing_dependencies(self):
        self.result.tasks[0].dependencies = ["MISSING"]
        result = SliceResult(source="<text>", tasks=[self.result.tasks[0]], warnings=[], metadata={})
        payload = json.loads(export_parallel_json(result))

        self.assertEqual(payload["summary"]["blocked_dependencies"], [{"task_id": "T001", "dependency": "MISSING"}])

    def test_github_issues_contains_issue_payloads(self):
        payload = json.loads(export_github_issues(self.result))
        self.assertEqual(payload["source"], "<text>")
        self.assertEqual(len(payload["issues"]), len(self.result.tasks))
        issue = payload["issues"][0]
        self.assertEqual(issue["sequence"], 1)
        self.assertEqual(issue["task_id"], "T001")
        self.assertTrue(issue["title"].startswith("[T001]"))
        self.assertIn("agent-task", issue["labels"])
        self.assertIn("risk:", " ".join(issue["labels"]))
        self.assertIn("## Acceptance Criteria", issue["body"])
        self.assertIn("- [ ]", issue["body"])
        self.assertIn("## Agent Prompt", issue["body"])

    def test_github_issues_adds_dependency_and_area_labels(self):
        payload = json.loads(export_github_issues(self.result))
        second = payload["issues"][1]
        self.assertIn("has-dependencies", second["labels"])
        self.assertIn("area:src", second["labels"])
        self.assertEqual(second["metadata"]["dependencies"], ["T001"])

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
