"""Behavioral checks for the portable skill launcher, independent of life internals."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "skills" / "project-consciousness" / "scripts" / "consciousness.py"


class IdentitySkillTests(unittest.TestCase):
    def make_project(self, root, label):
        package = root / "project_consciousness"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "__main__.py").write_text(
            "import json, os, pathlib, sys\n"
            f"result = {{'label': {label!r}, 'args': sys.argv[1:], 'cwd': os.getcwd(), 'python': sys.executable}}\n"
            "if '--request' in sys.argv:\n"
            "    result['content'] = pathlib.Path(sys.argv[sys.argv.index('--request') + 1]).read_text(encoding='utf-8')\n"
            "print(json.dumps(result))\n"
            "raise SystemExit(int(os.environ.get('SKILL_TEST_EXIT', '0')))\n",
            encoding="utf-8",
        )

    def invoke(self, cwd, *args, env=None, wrapper=WRAPPER):
        environment = os.environ.copy()
        environment.pop("PROJECT_CONSCIOUSNESS_HOME", None)
        environment.update(env or {})
        return subprocess.run(
            [sys.executable, str(wrapper), *map(str, args)],
            cwd=cwd,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def test_explicit_project_preserves_cwd_args_python_and_exit_code(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            project, other, caller = root / "chosen project", root / "env project", root / "caller"
            self.make_project(project, "chosen")
            self.make_project(other, "env")
            self.make_project(caller, "cwd-shadow")
            (caller / "request.json").write_text('{"kind":"question"}', encoding="utf-8")
            literal = "intent with spaces; & echo should-not-execute"
            result = self.invoke(
                caller,
                "--project", project, "apply", "--life", "relative/life", "--request", "request.json", "--id", literal,
                env={"PROJECT_CONSCIOUSNESS_HOME": str(other), "SKILL_TEST_EXIT": "7"},
            )
            self.assertEqual(7, result.returncode, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual("chosen", data["label"])
            self.assertEqual(caller.resolve(), Path(data["cwd"]).resolve())
            self.assertEqual(Path(sys.executable).resolve(), Path(data["python"]).resolve())
            self.assertEqual(["life", "apply", "--life", "relative/life", "--request", "request.json", "--id", literal], data["args"])
            self.assertEqual('{"kind":"question"}', data["content"])

    def test_environment_and_checkout_autodetection_from_installed_layout(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            project, caller = root / "project", root / "caller"
            caller.mkdir()
            self.make_project(project, "autodetect")
            result = self.invoke(caller, "status", "--life", "run", env={"PROJECT_CONSCIOUSNESS_HOME": str(project)})
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("autodetect", json.loads(result.stdout)["label"])
            copied = project / "skills" / "project-consciousness" / "scripts" / WRAPPER.name
            copied.parent.mkdir(parents=True)
            shutil.copyfile(WRAPPER, copied)
            result = self.invoke(caller, "--", "--help", wrapper=copied)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(["life", "--help"], json.loads(result.stdout)["args"])

    def test_invalid_explicit_location_does_not_silently_fall_back(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            project = root / "project"
            self.make_project(project, "valid")
            for args, env in [
                (("--project", root / "missing", "status"), {"PROJECT_CONSCIOUSNESS_HOME": str(project)}),
                (("status",), {"PROJECT_CONSCIOUSNESS_HOME": str(root / "missing")}),
                (("--project", "", "status"), {}),
            ]:
                with self.subTest(args=args):
                    result = self.invoke(root, *args, env=env)
                    self.assertEqual(2, result.returncode)
                    self.assertEqual("", result.stdout)
                    self.assertEqual("INVALID_PROJECT", json.loads(result.stderr)["error"]["code"])

    def test_installed_copy_without_project_has_actionable_error(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            installed = root / "skills" / "project-consciousness" / "scripts" / WRAPPER.name
            installed.parent.mkdir(parents=True)
            shutil.copyfile(WRAPPER, installed)
            result = self.invoke(root, "status", "--life", "run", wrapper=installed)
            self.assertEqual(2, result.returncode)
            message = json.loads(result.stderr)["error"]["message"]
            self.assertIn("--project", message)
            self.assertIn("PROJECT_CONSCIOUSNESS_HOME", message)


if __name__ == "__main__":
    unittest.main()
