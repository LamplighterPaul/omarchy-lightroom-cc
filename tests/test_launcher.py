import contextlib
import hashlib
import importlib.machinery
import importlib.util
import io
import json
import lzma
import os
from pathlib import Path
import tarfile
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

    def test_proton_selection_keeps_original_prefix_separate(self):
        original = self.app.PREFIX
        output = io.StringIO()
        with patch('sys.argv', ['omarchy-lightroom-cc', '--runner', 'proton', 'status']), contextlib.redirect_stdout(output):
            self.app.main()
        report = json.loads(output.getvalue())
        self.assertNotEqual(Path(report['prefix']), original)
        self.assertTrue(self.app.LR.is_relative_to(Path(report['prefix'])))
        self.assertFalse(report['workflow_verified'])

    def test_desktop_entry_preserves_selected_runner(self):
        self.app.RUNNER = 'staging'
        self.app.LR.parent.mkdir(parents=True)
        self.app.LR.touch()
        with patch.dict(os.environ, {'XDG_DATA_HOME': str(self.root)}), contextlib.redirect_stdout(io.StringIO()):
            self.app.integrate()
        entry = (self.root / 'applications/omarchy-lightroom-cc.desktop').read_text()
        self.assertIn('--runner staging --graphics x11 run', entry)

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

    def make_d3d12_archive(self, names):
        archive = self.root / "proton-test.tar.gz"
        with tarfile.open(archive, "w:gz") as package:
            for name in names:
                payload = ("new-" + name).encode()
                member = tarfile.TarInfo("proton-test/files/lib/wine/vkd3d-proton/x86_64-windows/" + name)
                member.size = len(payload)
                package.addfile(member, io.BytesIO(payload))
        return archive

    def test_d3d12_repair_is_scoped_and_preserves_first_backup(self):
        archive = self.make_d3d12_archive(("d3d12.dll", "d3d12core.dll"))
        original = self.app.PREFIX / "drive_c/windows/system32/d3d12.dll"
        original.parent.mkdir(parents=True)
        original.write_bytes(b"unrelated-prefix")
        target = self.app.DATA / "experiments/wine-staging-11.17/prefix/drive_c/windows/system32/d3d12.dll"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"original-staging")
        with patch.object(self.app, "fetch", return_value=archive), \
             patch.object(self.app, "manifest", return_value={"proton-ge": {"filename": archive.name}}), \
             patch.object(self.app, "environment", return_value={}), \
             patch.object(self.app, "run"), patch.object(self.app, "wine"), \
             patch("sys.argv", ["omarchy-lightroom-cc", "--runner", "staging", "repair-d3d12"]), \
             contextlib.redirect_stdout(io.StringIO()):
            self.app.main()
            self.app.main()
        self.assertEqual(original.read_bytes(), b"unrelated-prefix")
        self.assertEqual(target.read_bytes(), b"new-d3d12.dll")
        self.assertEqual(target.with_name("d3d12core.dll").read_bytes(), b"new-d3d12core.dll")
        self.assertEqual((self.app.PREFIX.parent / "repairs/d3d12/d3d12.dll").read_bytes(), b"original-staging")

    def test_incomplete_d3d12_pair_leaves_installation_running_and_unchanged(self):
        archive = self.make_d3d12_archive(("d3d12.dll",))
        target = self.app.PREFIX / "drive_c/windows/system32/d3d12.dll"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"original")
        with patch.object(self.app, "fetch", return_value=archive), \
             patch.object(self.app, "manifest", return_value={"proton-ge": {"filename": archive.name}}), \
             patch.object(self.app, "run") as execute:
            with self.assertRaisesRegex(RuntimeError, "missing the vkd3d-proton DLL pair"):
                self.app.repair_d3d12()
        execute.assert_not_called()
        self.assertEqual(target.read_bytes(), b"original")
