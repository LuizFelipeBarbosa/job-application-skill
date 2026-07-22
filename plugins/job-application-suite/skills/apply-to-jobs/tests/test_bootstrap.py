from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "bootstrap.py"
SPEC = importlib.util.spec_from_file_location("bootstrap", MODULE_PATH)
assert SPEC and SPEC.loader
bootstrap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bootstrap)


class BootstrapTests(unittest.TestCase):
    def test_workspace_root_uses_nearest_git_ancestor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".git").mkdir()
            nested = root / "one" / "two"
            nested.mkdir(parents=True)

            self.assertEqual(bootstrap.workspace_root(nested), root.resolve())

    def test_main_runs_locked_uv_sync_in_workspace_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            runtime = bootstrap.runtime_python(workspace / ".runtime" / "venv")
            runtime.parent.mkdir(parents=True)
            runtime.touch()

            with (
                mock.patch.object(sys, "argv", ["bootstrap.py", "--workspace", directory]),
                mock.patch.object(bootstrap.shutil, "which", return_value="/usr/local/bin/uv"),
                mock.patch.object(bootstrap.subprocess, "run") as run,
            ):
                bootstrap.main()

            command = run.call_args.args[0]
            self.assertEqual(command[0:2], ["/usr/local/bin/uv", "sync"])
            self.assertIn("--locked", command)
            self.assertIn("--no-dev", command)
            self.assertIn("--no-install-project", command)
            self.assertEqual(command[command.index("--python") + 1], sys.executable)
            self.assertTrue(run.call_args.kwargs["check"])
            self.assertEqual(
                run.call_args.kwargs["env"]["UV_PROJECT_ENVIRONMENT"],
                str(workspace.resolve() / ".runtime" / "venv"),
            )

    def test_main_requires_uv(self) -> None:
        with (
            tempfile.TemporaryDirectory() as directory,
            mock.patch.object(sys, "argv", ["bootstrap.py", "--workspace", directory]),
            mock.patch.object(bootstrap.shutil, "which", return_value=None),
        ):
            with self.assertRaisesRegex(SystemExit, "uv 0.9.29 or newer is required"):
                bootstrap.main()


if __name__ == "__main__":
    unittest.main()
