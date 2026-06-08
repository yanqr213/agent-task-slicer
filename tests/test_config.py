import json
import os
import tempfile
import unittest

from agent_task_slicer.config import SlicerConfig, load_config, merge_config_fragments, validate_config
from agent_task_slicer.errors import ConfigError


class ConfigTests(unittest.TestCase):
    def test_default_config_is_valid(self):
        config = SlicerConfig()
        self.assertGreater(config.max_tasks, 0)
        self.assertIn("src", config.path_roots)

    def test_validate_accepts_known_values(self):
        config = validate_config({"max_tasks": 3, "package_prefix": "A"})
        self.assertEqual(config.max_tasks, 3)
        self.assertEqual(config.package_prefix, "A")

    def test_validate_rejects_unknown_key(self):
        with self.assertRaises(ConfigError):
            validate_config({"surprise": True})

    def test_validate_rejects_non_integer_max_tasks(self):
        with self.assertRaises(ConfigError):
            validate_config({"max_tasks": "ten"})

    def test_validate_rejects_boolean_as_integer(self):
        with self.assertRaises(ConfigError):
            validate_config({"max_tasks": True})

    def test_validate_rejects_out_of_range_max_tasks(self):
        with self.assertRaises(ConfigError):
            validate_config({"max_tasks": 0})

    def test_validate_rejects_non_list_commands(self):
        with self.assertRaises(ConfigError):
            validate_config({"default_test_commands": "python -m unittest"})

    def test_validate_rejects_bad_risk_keyword_score(self):
        with self.assertRaises(ConfigError):
            validate_config({"risk_keywords": {"auth": 9}})

    def test_validate_rejects_bad_prefix(self):
        with self.assertRaises(ConfigError):
            validate_config({"package_prefix": "BAD PREFIX"})

    def test_validate_rejects_bad_boolean(self):
        with self.assertRaises(ConfigError):
            validate_config({"infer_dependencies": "yes"})

    def test_load_config_reads_json_file(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".json") as handle:
            json.dump({"max_tasks": 7, "package_prefix": "X"}, handle)
            path = handle.name
        try:
            config = load_config(path)
            self.assertEqual(config.max_tasks, 7)
            self.assertEqual(config.package_prefix, "X")
        finally:
            os.remove(path)

    def test_load_config_missing_file(self):
        with self.assertRaises(ConfigError):
            load_config("missing-config.json")

    def test_load_config_invalid_json(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".json") as handle:
            handle.write("{bad json")
            path = handle.name
        try:
            with self.assertRaises(ConfigError):
                load_config(path)
        finally:
            os.remove(path)

    def test_load_config_applies_overrides(self):
        config = load_config(overrides={"max_tasks": 2})
        self.assertEqual(config.max_tasks, 2)

    def test_merge_config_fragments_later_wins(self):
        config = merge_config_fragments([{"max_tasks": 2}, {"max_tasks": 5}])
        self.assertEqual(config.max_tasks, 5)


if __name__ == "__main__":
    unittest.main()

