import contextlib
import hashlib
import importlib.machinery
import importlib.util
import io
import lzma
import os
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch


class LauncherTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lrcc-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        path = Path(__file__).resolve().parents[1] / "bin/omarchy-lightroom-cc"
        spec = importlib.util.spec_from_loader("launcher", importlib.machinery.SourceFileLoader("launcher", str(path)))
        self.app = importlib.util.module_from_spec(spec)
        with patch.dict(os.environ, {"LRCC_DATA": str(self.root / "app data")}):
            spec.loader.exec_module(self.app)

    def test_environment_cannot_inherit_unrelated_prefix_or_wine(self):
        wine = self.app.RUNTIME / "bin/wine"
        wine.parent.mkdir(parents=True)
        wine.touch()
        with patch.dict(os.environ, {"WINEPREFIX": "/wrong", "WINE": "/wrong/wine", "WINESERVER": "/wrong/server"}):
            env = self.app.environment()
        self.assertEqual(env["WINEPREFIX"], str(self.app.PREFIX))
        self.assertEqual(env["WINE"], str(wine))
        self.assertEqual(env["WINESERVER"], str(wine.parent / "wineserver"))

    def test_download_checksum_failure_never_promotes_partial(self):
        spec = {"asset": {"filename": "asset.bin", "url": "https://example.invalid/asset", "sha256": hashlib.sha256(b"good").hexdigest()}}
        def download(args):
            Path(args[args.index("--output") + 1]).write_bytes(b"wrong")
        with patch.object(self.app, "manifest", return_value=spec), patch.object(self.app, "run", side_effect=download):
            with self.assertRaisesRegex(RuntimeError, "Checksum mismatch"):
                self.app.fetch("asset")
        self.assertFalse((self.app.DATA / "cache/asset.bin").exists())

    def test_presence_is_not_workflow_verification(self):
        for exe in (self.app.CC, self.app.LR):
            exe.parent.mkdir(parents=True, exist_ok=True)
            exe.touch()
        report = self.app.status()
        self.assertTrue(report["lightroom_exe_present"])
        self.assertFalse(report["workflow_verified"])

    def test_verified_cache_does_not_access_network(self):
        dest = self.app.DATA / "cache/asset.bin"
        dest.parent.mkdir(parents=True)
        dest.write_bytes(b"good")
        spec = {"asset": {"filename": "asset.bin", "sha256": hashlib.sha256(b"good").hexdigest()}}
        with patch.object(self.app, "manifest", return_value=spec), patch.object(self.app, "run") as execute, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.app.fetch("asset"), dest)
        execute.assert_not_called()

    def test_windows_archive_paths_are_normalized(self):
        archive = self.root / "payload.zip"
        with zipfile.ZipFile(archive, "w") as z:
            data = b"\x18" + lzma.compress(b"test", format=lzma.FORMAT_RAW,
                filters=[{"id": lzma.FILTER_LZMA2, "dict_size": 16 * 1024 * 1024}])
            z.writestr(r"1\Adobe Lightroom\folder\example.txt", data)
        target = self.root / "application"
        self.app.extract_lightroom(archive, target)
        self.assertEqual((target / "folder/example.txt").read_text(), "test")

    def test_windows_archive_traversal_is_rejected(self):
        archive = self.root / "payload.zip"
        with zipfile.ZipFile(archive, "w") as z:
            z.writestr(r"1\Adobe Lightroom\..\outside.txt", "test")
        with self.assertRaisesRegex(RuntimeError, "Unsafe archive path"):
            self.app.extract_lightroom(archive, self.root / "application")
        self.assertFalse((self.root / "outside.txt").exists())

    def test_adobe_decoder_rejects_truncated_stream(self):
        data = b"\x18" + lzma.compress(b"MZ" + bytes(range(256)) * 100, format=lzma.FORMAT_RAW,
            filters=[{"id": lzma.FILTER_LZMA2, "dict_size": 16 * 1024 * 1024}])
        with self.assertRaises((EOFError, lzma.LZMAError)):
            self.app.decode_adobe_file(io.BytesIO(data[:-8]), io.BytesIO())

    def test_adobe_decoder_bounds_dictionary_allocation(self):
        with self.assertRaisesRegex(RuntimeError, "dictionary property"):
            self.app.decode_adobe_file(io.BytesIO(b"\xffgarbage"), io.BytesIO())
