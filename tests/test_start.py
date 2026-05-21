import unittest
from unittest.mock import patch

import start


class StartScriptPnpmDiscoveryTests(unittest.TestCase):
    def test_find_pnpm_command_prefers_direct_pnpm(self):
        pnpm_name = "pnpm.cmd" if start.IS_WINDOWS else "pnpm"
        pnpm_path = "C:/tools/pnpm.cmd" if start.IS_WINDOWS else "/usr/local/bin/pnpm"

        def fake_which(candidate: str):
            return pnpm_path if candidate == pnpm_name else None

        with patch.object(start.shutil, "which", side_effect=fake_which):
            self.assertEqual(start.find_pnpm_command(), [pnpm_path])

    def test_find_pnpm_command_falls_back_to_corepack(self):
        corepack_name = "corepack.cmd" if start.IS_WINDOWS else "corepack"
        corepack_path = "C:/Program Files/nodejs/corepack.cmd" if start.IS_WINDOWS else "/usr/local/bin/corepack"

        def fake_which(candidate: str):
            return corepack_path if candidate == corepack_name else None

        with patch.object(start.shutil, "which", side_effect=fake_which):
            self.assertEqual(start.find_pnpm_command(), [corepack_path, "pnpm"])

    def test_start_frontend_appends_dev_arguments(self):
        calls: list[tuple[list[str], object]] = []

        def fake_popen(command, cwd):
            calls.append((command, cwd))
            return object()

        with patch.object(start.subprocess, "Popen", side_effect=fake_popen):
            start.start_frontend(["corepack", "pnpm"])

        self.assertEqual(calls[0][0], ["corepack", "pnpm", "dev", "--port", str(start.FRONTEND_PORT)])
        self.assertEqual(calls[0][1], start.ROOT / "frontend")


if __name__ == "__main__":
    unittest.main()
