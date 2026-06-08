import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from agent_task_slicer import __version__
from agent_task_slicer.cli import main
from agent_task_slicer.errors import EXIT_CONFIG_ERROR, EXIT_INPUT_ERROR, EXIT_OK


INPUT = "# X\n## Task: build parser\n- Implement `src/parser.py`.\n"


class CliTests(unittest.TestCase):
    def run_cli(self, args, stdin=""):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch.object(sys, "stdin", io.StringIO(stdin)):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_cli_reads_stdin_markdown(self):
        code, stdout, stderr = self.run_cli(["-"], stdin=INPUT)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("# Agent Task Slices", stdout)
        self.assertEqual(stderr, "")

    def test_cli_outputs_json(self):
        code, stdout, _ = self.run_cli(["-", "--format", "json"], stdin=INPUT)
        self.assertEqual(code, EXIT_OK)
        payload = json.loads(stdout)
        self.assertEqual(len(payload["tasks"]), 1)

    def test_cli_outputs_dot(self):
        code, stdout, _ = self.run_cli(["-", "--format", "dot"], stdin=INPUT)
        self.assertEqual(code, EXIT_OK)
        self.assertTrue(stdout.startswith("digraph"))

    def test_cli_reads_file(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".md") as handle:
            handle.write(INPUT)
            path = handle.name
        try:
            code, stdout, _ = self.run_cli([path])
            self.assertEqual(code, EXIT_OK)
            self.assertIn(path, stdout)
        finally:
            os.remove(path)

    def test_cli_writes_output_file(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".md") as input_handle:
            input_handle.write(INPUT)
            input_path = input_handle.name
        output_path = input_path + ".out.md"
        try:
            code, stdout, _ = self.run_cli([input_path, "-o", output_path])
            self.assertEqual(code, EXIT_OK)
            self.assertEqual(stdout, "")
            with open(output_path, "r", encoding="utf-8") as handle:
                self.assertIn("# Agent Task Slices", handle.read())
        finally:
            os.remove(input_path)
            if os.path.exists(output_path):
                os.remove(output_path)

    def test_cli_missing_input_returns_input_error(self):
        code, _, stderr = self.run_cli(["missing.md"])
        self.assertEqual(code, EXIT_INPUT_ERROR)
        self.assertIn("not found", stderr)

    def test_cli_empty_stdin_returns_input_error(self):
        code, _, stderr = self.run_cli(["-"], stdin=" ")
        self.assertEqual(code, EXIT_INPUT_ERROR)
        self.assertIn("stdin is empty", stderr)

    def test_cli_invalid_config_returns_config_error(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".json") as handle:
            handle.write("{bad json")
            path = handle.name
        try:
            code, _, stderr = self.run_cli(["-", "-c", path], stdin=INPUT)
            self.assertEqual(code, EXIT_CONFIG_ERROR)
            self.assertIn("invalid JSON", stderr)
        finally:
            os.remove(path)

    def test_cli_config_changes_prefix(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".json") as handle:
            json.dump({"package_prefix": "AG"}, handle)
            path = handle.name
        try:
            code, stdout, _ = self.run_cli(["-", "-c", path], stdin=INPUT)
            self.assertEqual(code, EXIT_OK)
            self.assertIn("## AG001", stdout)
        finally:
            os.remove(path)

    def test_cli_overrides_max_tasks(self):
        text = "# X\n## Task: one\n- Build one\n## Task: two\n- Build two\n"
        code, stdout, _ = self.run_cli(["-", "--max-tasks", "1"], stdin=text)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("Tasks: 1", stdout)

    def test_cli_prefix_override(self):
        code, stdout, _ = self.run_cli(["-", "--prefix", "Z"], stdin=INPUT)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("## Z001", stdout)

    def test_cli_no_deps(self):
        text = "# X\n## Task: one\n- Build `src/a.py`\n## Task: two\n- Build `src/a.py`\n"
        code, stdout, _ = self.run_cli(["-", "--no-deps"], stdin=text)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("## T002", stdout)

    def test_cli_version_raises_system_exit_from_argparse(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            with self.assertRaises(SystemExit) as ctx:
                main(["--version"])
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn(__version__, stdout.getvalue())


if __name__ == "__main__":
    unittest.main()

