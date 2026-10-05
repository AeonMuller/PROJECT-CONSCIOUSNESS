import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from project_consciousness.__main__ import main, parse_seeds
from project_consciousness.contracts import LabError


class CLITests(unittest.TestCase):
    def invoke(self, *args):
        output, error = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            code = main(list(map(str, args)))
        return code, json.loads(output.getvalue() or error.getvalue())

    def test_real_run_resume_replay_and_fork_commands(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            run, child = folder / "run", folder / "child"
            condition = folder / "condition.toml"
            condition.write_text('read_mode = "block_all"\n', encoding="utf-8")
            code, result = self.invoke("run", "--out", run, "--ticks", 4)
            self.assertEqual(0, code)
            self.assertEqual(4, result["tick"])
            self.assertIsNone(result["success_rate"])
            self.assertTrue((run / "decisions.jsonl").is_file())
            code, result = self.invoke("fork", "--run", run, "--tick", 4, "--condition", condition, "--out", child)
            self.assertEqual(0, code)
            self.assertEqual(4, result["tick"])
            code, result = self.invoke("resume", "--run", run, "--ticks", 6)
            self.assertEqual(0, code)
            self.assertEqual(2, result["completed_episodes"])
            code, result = self.invoke("replay", "--run", run, "--mode", "recompute", "--verify")
            self.assertEqual(0, code)
            self.assertTrue(result["valid"])
            code, result = self.invoke("status", "--run", run)
            self.assertEqual(0, code)
            self.assertEqual(10, result["tick"])

    def test_structured_errors_do_not_create_output_for_invalid_ticks(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "never-created"
            code, result = self.invoke("run", "--out", path, "--ticks", -1)
            self.assertEqual(2, code)
            self.assertEqual("INVALID_INPUT", result["error"]["code"])
            self.assertFalse(path.exists())

    def test_seeds_are_bounded_half_open_and_reject_malformed(self):
        self.assertEqual([100, 101, 102], parse_seeds("100:103"))
        for value in ("1", "1:1", "-1:2", "0:10001", "a:b", "1:2:3"):
            with self.assertRaises(LabError):
                parse_seeds(value)


if __name__ == "__main__":
    unittest.main()
