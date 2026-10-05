import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from project_consciousness.__main__ import main


class LearningCLITests(unittest.TestCase):
    def invoke(self, *args):
        output, error = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            code = main(list(map(str, args)))
        return code, json.loads(output.getvalue() or error.getvalue())

    def test_sectioned_config_learning_freeze_resume_and_status(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "run.toml"
            config.write_text('[agent]\npolicy_mode="learned"\ndelay=1\n[task]\nkind="reversal-v1"\nreversal_episode=3\n', encoding="utf-8")
            freeze = root / "freeze.toml"
            freeze.write_text('learning_enabled=false\n', encoding="utf-8")
            code, result = self.invoke("run", "--config", config, "--ticks", 9, "--out", root / "run")
            self.assertEqual(code, 0, result)
            code, status = self.invoke("status", "--run", root / "run")
            self.assertEqual(status["learner"]["updates"], 3)
            code, result = self.invoke("fork", "--run", root / "run", "--condition", freeze, "--out", root / "frozen")
            self.assertEqual(code, 0, result)
            code, result = self.invoke("resume", "--run", root / "frozen", "--ticks", 9)
            self.assertEqual(code, 0, result)
            _, frozen = self.invoke("status", "--run", root / "frozen")
            self.assertEqual(frozen["learner"], status["learner"])
            code, result = self.invoke("replay", "--run", root / "frozen", "--verify")
            self.assertEqual(code, 0, result)
            self.assertTrue(result["valid"])

    def test_l1_command_and_report_routing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protocol = root / "l1.toml"
            protocol.write_text('[experiment]\nprotocol="L1"\nacquisition_episodes=3\nadaptation_episodes=3\nbootstrap_samples=20\n[agent]\npolicy_mode="learned"\ndelay=1\n[task]\nkind="reversal-v1"\nreversal_episode=3\n', encoding="utf-8")
            destination = root / "experiment"
            code, result = self.invoke("experiment", "--protocol", protocol, "--seeds", "700:702", "--out", destination)
            self.assertEqual(code, 0, result)
            self.assertEqual(result["status"], "completed")
            report = destination / "report.md"
            before = report.read_bytes()
            code, result = self.invoke("report", "--experiment", destination)
            self.assertEqual(code, 0, result)
            self.assertEqual(report.read_bytes(), before)

    def test_old_protocols_reject_learning_and_section_mix_without_creating_run(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "invalid.toml"
            for protocol in ("E0", "E1"):
                config.write_text(f'[experiment]\nprotocol="{protocol}"\n[agent]\npolicy_mode="learned"\n', encoding="utf-8")
                code, result = self.invoke("experiment", "--protocol", config, "--out", root / "absent")
                self.assertEqual(code, 2, result)
                self.assertFalse((root / "absent").exists())
            config.write_text('delay=3\n[task]\nkind="reversal-v1"\n', encoding="utf-8")
            code, result = self.invoke("run", "--config", config, "--out", root / "absent")
            self.assertEqual(code, 2, result)
            self.assertFalse((root / "absent").exists())


if __name__ == "__main__":
    unittest.main()
