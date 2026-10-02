"""Reproduce Windows replacement failures without collection or live data."""

import ctypes
import errno
import json
import os
import tempfile
import unittest
from ctypes import wintypes
from pathlib import Path
from unittest.mock import patch

from collector.run_log import write_json


class PersistenceTests(unittest.TestCase):
    def test_persistent_denial_preserves_previous_json_and_stops_after_six_attempts(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "run.json"
            destination.write_text('{"value": 1}', encoding="utf-8")
            with patch.object(Path, "replace", side_effect=PermissionError(errno.EACCES, "Synthetic persistent lock")) as replace, patch("collector.persistence.time.sleep") as sleep:
                with self.assertRaises(PermissionError):
                    write_json(destination, {"value": 2})
            self.assertEqual(replace.call_count, 6)
            self.assertEqual(sleep.call_count, 5)
            self.assertAlmostEqual(sum(call.args[0] for call in sleep.call_args_list), 3.1)
            self.assertEqual(json.loads(destination.read_text(encoding="utf-8")), {"value": 1})
            self.assertEqual(json.loads(destination.with_suffix(".json.tmp").read_text(encoding="utf-8")), {"value": 2})

    def test_other_filesystem_errors_are_not_retried(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "run.json"
            with patch.object(Path, "replace", side_effect=OSError(errno.ENOSPC, "Synthetic disk full")) as replace, patch("collector.persistence.time.sleep") as sleep:
                with self.assertRaises(OSError):
                    write_json(destination, {"value": 2})
            replace.assert_called_once()
            sleep.assert_not_called()

    @unittest.skipUnless(os.name == "nt", "Requires Windows file sharing semantics")
    def test_run_log_recovers_after_windows_denies_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "run.json"
            destination.write_text('{"value": 1}', encoding="utf-8")
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
            kernel.CreateFileW.restype = wintypes.HANDLE
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel.CloseHandle.restype = wintypes.BOOL
            # Permit reads/writes but deny deletion/replacement until released.
            handle = kernel.CreateFileW(str(destination), 0x80000000, 3, None, 3, 0x80, None)
            self.assertNotEqual(handle, ctypes.c_void_p(-1).value)
            real_replace = Path.replace
            denied = []

            def replace(temporary, target):
                nonlocal handle
                try:
                    return real_replace(temporary, target)
                except PermissionError as exc:
                    denied.append(exc.winerror)
                    kernel.CloseHandle(handle)
                    handle = None
                    raise

            try:
                with patch.object(Path, "replace", replace), patch("time.sleep"):
                    write_json(destination, {"value": 2})
                self.assertEqual(denied, [5])
                self.assertEqual(json.loads(destination.read_text(encoding="utf-8")), {"value": 2})
                self.assertFalse(destination.with_suffix(".json.tmp").exists())
            finally:
                if handle is not None:
                    kernel.CloseHandle(handle)


if __name__ == "__main__":
    unittest.main()
