import os
import tempfile
import unittest

from agent_task_slicer.errors import InputError
from agent_task_slicer.parser import (
    clean_text,
    extract_bullets,
    extract_checklist_items,
    extract_paths,
    parse_file,
    parse_text,
    unique_preserve_order,
)


class ParserTests(unittest.TestCase):
    def test_parse_markdown_headings(self):
        doc = parse_text("# Title\n\n## Task A\nDo thing\n\n## Task B\nDo other\n", source="x.md")
        self.assertEqual(doc.title, "Title")
        self.assertEqual(len(doc.sections), 3)
        self.assertEqual(doc.sections[1].title, "Task A")
        self.assertEqual(doc.sections[1].start_line, 3)

    def test_parse_plain_text_creates_fallback_section(self):
        doc = parse_text("Implement parser for src/app.py\n- Add tests", source="note.txt")
        self.assertEqual(len(doc.sections), 1)
        self.assertEqual(doc.sections[0].title, "note.txt")

    def test_parse_text_rejects_empty_input(self):
        with self.assertRaises(InputError):
            parse_text(" \n\t")

    def test_parse_file_reads_utf8(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".md") as handle:
            handle.write("# 你好\n\n内容")
            path = handle.name
        try:
            doc = parse_file(path)
            self.assertEqual(doc.title, "你好")
        finally:
            os.remove(path)

    def test_parse_file_missing_raises(self):
        with self.assertRaises(InputError):
            parse_file("missing-file.md")

    def test_parse_file_rejects_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(InputError):
                parse_file(folder)

    def test_parse_file_invalid_utf8_raises(self):
        fd, path = tempfile.mkstemp(suffix=".md")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(b"\xff\xfe\xff")
            with self.assertRaises(InputError):
                parse_file(path)
        finally:
            os.remove(path)

    def test_extract_checklist_items(self):
        items = extract_checklist_items("- [ ] first\n- [x] second\n- normal")
        self.assertEqual(items, ["first", "second"])

    def test_extract_bullets_supports_ordered_and_unordered(self):
        bullets = extract_bullets("- one\n* two\n1. three\n2) four")
        self.assertEqual(bullets, ["one", "two", "three", "four"])

    def test_extract_paths_from_inline_code_and_plain_text(self):
        paths = extract_paths("Update `src/app/main.py` and tests/test_main.py.")
        self.assertIn("src/app/main.py", paths)
        self.assertIn("tests/test_main.py", paths)

    def test_extract_paths_normalizes_backslashes(self):
        paths = extract_paths(r"Update `src\app\main.py`.")
        self.assertEqual(paths, ["src/app/main.py"])

    def test_extract_paths_ignores_urls(self):
        self.assertEqual(extract_paths("See https://example.com/a/b for context"), [])

    def test_clean_text_strips_markdown_noise(self):
        self.assertEqual(clean_text("###  Task: build  parser  "), "Task: build parser")

    def test_unique_preserve_order(self):
        self.assertEqual(unique_preserve_order(["a", "b", "a", "c"]), ["a", "b", "c"])


if __name__ == "__main__":
    unittest.main()

