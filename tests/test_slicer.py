import unittest

from agent_task_slicer.config import SlicerConfig
from agent_task_slicer.heuristics import generated_acceptance_criteria, risk_reasons, risk_score, suggested_commands
from agent_task_slicer.models import TaskPackage
from agent_task_slicer.slicer import TaskSlicer, slice_text


SAMPLE = """# Project

## 任务：读取 Markdown 和 issue

- 实现 Markdown 标题、checklist、普通 bullet 的解析。
- 读取 `src/inbox/parser.py` 与 `tests/test_parser.py`。
- 验收：空输入应返回明确错误。

## 任务：生成 agent 工作包

- 基于解析结果生成目标、范围、输入文件、验收标准。
- 依赖：读取 Markdown 和 issue。
- 风险：如果需求涉及 auth、database migration、payment，需要高风险提示。

## 任务：导出结果

- 支持 Markdown、JSON、Graphviz DOT。
- 更新 `src/inbox/exporters.py`、`tests/test_exporters.py`。
"""


class SlicerTests(unittest.TestCase):
    def test_slice_text_returns_tasks(self):
        result = slice_text(SAMPLE)
        self.assertGreaterEqual(len(result.tasks), 3)
        self.assertEqual(result.tasks[0].id, "T001")

    def test_task_has_goal_scope_and_criteria(self):
        task = slice_text(SAMPLE).tasks[0]
        self.assertTrue(task.goal)
        self.assertTrue(task.scope)
        self.assertTrue(task.acceptance_criteria)

    def test_input_files_are_extracted(self):
        task = slice_text(SAMPLE).tasks[0]
        self.assertIn("src/inbox/parser.py", task.input_files)
        self.assertIn("tests/test_parser.py", task.input_files)

    def test_explicit_dependency_is_resolved_to_task_id(self):
        result = slice_text(SAMPLE)
        second = result.tasks[1]
        self.assertIn("T001", second.dependencies)
        self.assertNotIn("解析结果生成目标", second.dependencies)

    def test_shared_path_dependency_is_inferred(self):
        text = """# X
## Task: update API
- Change `src/api.py`.
## Task: test API
- Add tests for `src/api.py`.
"""
        result = slice_text(text)
        self.assertIn("T001", result.tasks[1].dependencies)

    def test_no_deps_config_disables_dependency_inference(self):
        config = SlicerConfig(infer_dependencies=False)
        result = TaskSlicer(config).slice_text(SAMPLE)
        self.assertNotIn("T001", result.tasks[1].dependencies)

    def test_max_tasks_limits_output(self):
        config = SlicerConfig(max_tasks=1)
        result = TaskSlicer(config).slice_text(SAMPLE)
        self.assertEqual(len(result.tasks), 1)
        self.assertTrue(result.warnings)

    def test_prefix_config_changes_ids(self):
        config = SlicerConfig(package_prefix="A")
        result = TaskSlicer(config).slice_text(SAMPLE)
        self.assertEqual(result.tasks[0].id, "A001")

    def test_fallback_task_for_plain_requirement(self):
        result = slice_text("请把系统做得更稳定，补充错误处理和测试。", source="plain")
        self.assertEqual(len(result.tasks), 1)
        self.assertIn("梳理并实现", result.tasks[0].title)

    def test_low_confidence_can_be_disabled(self):
        config = SlicerConfig(include_low_confidence_tasks=False)
        result = TaskSlicer(config).slice_text("只是一些背景信息，没有动作。")
        self.assertEqual(result.tasks, [])

    def test_risk_score_detects_security_keywords(self):
        task = TaskPackage(
            id="T001",
            title="Implement auth database migration",
            goal="",
            scope=["auth", "database migration"],
            input_files=["src/auth.py"],
            acceptance_criteria=[],
            risks=[],
            risk_score=1,
            suggested_commands=[],
            dependencies=[],
        )
        self.assertEqual(risk_score(task, SlicerConfig()), 5)

    def test_risk_reasons_default_to_regular_risk(self):
        task = TaskPackage(
            id="T001",
            title="Update copy",
            goal="",
            scope=["copy"],
            input_files=["docs/readme.md"],
            acceptance_criteria=[],
            risks=[],
            risk_score=1,
            suggested_commands=[],
            dependencies=[],
        )
        self.assertEqual(risk_reasons(task, SlicerConfig()), ["常规实现风险。"])

    def test_generated_acceptance_mentions_input_files(self):
        task = TaskPackage(
            id="T001",
            title="Update parser",
            goal="",
            scope=["parse"],
            input_files=["src/parser.py"],
            acceptance_criteria=[],
            risks=[],
            risk_score=1,
            suggested_commands=[],
            dependencies=[],
        )
        criteria = generated_acceptance_criteria(task)
        self.assertTrue(any("src/parser.py" in item.text for item in criteria))

    def test_suggested_commands_use_default_for_python_paths(self):
        task = TaskPackage(
            id="T001",
            title="Update parser",
            goal="",
            scope=["parse"],
            input_files=["src/parser.py"],
            acceptance_criteria=[],
            risks=[],
            risk_score=1,
            suggested_commands=[],
            dependencies=[],
        )
        self.assertEqual(suggested_commands(task, SlicerConfig()), ["python -m unittest"])

    def test_metadata_contains_title_and_section_count(self):
        result = slice_text(SAMPLE, source="sample.md")
        self.assertEqual(result.source, "sample.md")
        self.assertEqual(result.metadata["title"], "Project")
        self.assertGreater(result.metadata["sections"], 0)

    def test_section_without_task_marker_can_split_bullets(self):
        text = """# Plan
## Implementation
- Build parser module
- Add JSON exporter
"""
        result = slice_text(text)
        self.assertGreaterEqual(len(result.tasks), 2)

    def test_doc_keyword_infers_docs_path(self):
        result = slice_text("# X\n## Task: document API\nAdd docs for CLI.")
        self.assertIn("docs/", result.tasks[0].input_files)

    def test_test_keyword_infers_tests_path(self):
        result = slice_text("# X\n## Task: add tests\nEnsure parser tests exist.")
        self.assertIn("tests/", result.tasks[0].input_files)

    def test_based_on_phrase_is_not_treated_as_dependency(self):
        text = """# X
## 任务：生成工作包
- 基于解析结果生成目标、范围、输入文件、验收标准。
"""
        result = slice_text(text)
        self.assertEqual(result.tasks[0].dependencies, [])


if __name__ == "__main__":
    unittest.main()
