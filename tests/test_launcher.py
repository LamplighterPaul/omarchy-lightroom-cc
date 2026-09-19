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

    def test_custom_proton_launch_does_not_wait_for_its_own_helpers(self):
        self.app.PROTON = True
        self.app.RUNNER = "lightroom-omarchy-proton"
        with patch.object(self.app, "environment", return_value={}), patch.object(self.app, "run") as run:
            self.app.wine(Path("/prefix/Adobe/lightroom.exe"))
            self.assertEqual(run.call_args.kwargs["env"]["PROTON_VERB"], "run")
        with patch.object(self.app, "environment", return_value={"PROTON_VERB": "waitforexitandrun"}), patch.object(self.app, "run") as run:
            self.app.wine(Path("/prefix/Adobe/lightroom.exe"))
            self.assertEqual(run.call_args.kwargs["env"]["PROTON_VERB"], "waitforexitandrun")
        with patch.object(self.app, "environment", return_value={"PROTON_VERB": "run"}), patch.object(self.app, "run") as run:
            self.app.wine("reg", "query", "HKCU")
            self.assertEqual(run.call_args.kwargs["env"]["PROTON_VERB"], "runinprefix")

    def test_scale_follows_destination_monitor_not_current_focus(self):
        monitors = [{"name": "internal", "scale": 2, "focused": False},
                    {"name": "external", "scale": 1, "focused": True}]
        self.assertEqual(self.app.desktop_scale(monitors, [{"id": 10, "monitor": "internal"}]), 192)
        self.assertEqual(self.app.desktop_scale(monitors, []), 96)

    def test_candidate_runtime_is_named_and_identified(self):
        runtime = self.app.DATA / 'runtimes/candidate'
        runtime.mkdir(parents=True)
        (runtime / 'lightroom-omarchy-proton.json').write_text(json.dumps({'name': 'lightroom-omarchy-proton'}))
        self.assertEqual(self.app.selected_proton_runtime('candidate'), runtime / 'files')
        for invalid in ('../candidate', '/candidate', 'missing'):
            with self.assertRaises(RuntimeError):
                self.app.selected_proton_runtime(invalid)

    def staged_profile(self):
        self.app.SCRIPT = self.root / 'bin/launcher'
        config = self.root / 'config/performance-profile.json'
        config.parent.mkdir()
        runtime = self.app.DATA / 'runtimes/tested'
        component = runtime / 'files/lib/test.dll'
        component.parent.mkdir(parents=True)
        component.write_bytes(b'tested component')
        (runtime / 'files/bin').mkdir()
        (runtime / 'files/bin/wine').touch()
        (runtime / 'lightroom-omarchy-proton.json').write_text(json.dumps({
            'name': 'lightroom-omarchy-proton', 'version': 'test'}))
        config.write_text(json.dumps({'runtime': 'tested', 'version': 'test',
            'components': {'files/lib/test.dll': hashlib.sha256(component.read_bytes()).hexdigest()},
            'limiter': 'mangohud', 'retain_loupe': '1'}))
        layer = self.app.DATA / 'tools/mangohud/layers/MangoHud.x86_64.json'
        layer.parent.mkdir(parents=True)
        layer.touch()
        return runtime, component, layer

    def test_profile_selection_is_persistent_and_rejects_modified_build(self):
        runtime, component, layer = self.staged_profile()
        self.assertEqual(self.app.saved_profile(), 'stable')
        with contextlib.redirect_stdout(io.StringIO()):
            self.app.save_profile('performance')
            self.assertEqual(self.app.saved_profile(), 'performance')
            self.assertEqual(self.app.configure_profile('performance'), runtime / 'files')
            self.app.save_profile('stable')
        component.write_bytes(b'unreviewed replacement')
        with self.assertRaisesRegex(RuntimeError, 'differs from the tested build'):
            self.app.save_profile('performance')
        self.assertEqual(self.app.saved_profile(), 'stable')

    def test_profile_requires_limiter_but_stable_recovery_does_not(self):
        runtime, component, layer = self.staged_profile()
        layer.unlink()
        with self.assertRaisesRegex(RuntimeError, 'staged limiter'):
            self.app.save_profile('performance')
        self.assertFalse((self.app.DATA / 'launch-profile.json').exists())
        (self.app.DATA / 'launch-profile.json').write_text('{broken')
        with contextlib.redirect_stdout(io.StringIO()):
            self.app.save_profile('stable')
        self.assertEqual(self.app.saved_profile(), 'stable')

    def test_limiter_repair_does_not_require_a_working_saved_profile(self):
        with patch('sys.argv', ['launcher', '--runner', 'lightroom-omarchy-proton', 'stage-mangohud']), \
             patch.object(self.app, 'stage_mangohud') as stage, \
             patch.object(self.app, 'configure_profile') as configure:
            self.app.main()
        stage.assert_called_once()
        configure.assert_not_called()

    def test_profile_binds_limiter_and_retention_with_explicit_overrides(self):
        self.staged_profile()
        self.app.RUNTIME = self.app.configure_profile('performance')
        self.app.PROTON = True
        self.app.RUNNER = 'lightroom-omarchy-proton'
        self.app.PRESENT_HZ = 120
        (self.app.PREFIX.parent / 'profile.json').write_text(json.dumps({'windows_username': 'test'}))
        with patch.dict(os.environ, {}, clear=True):
            env = self.app.environment()
            self.assertIn('dxgi.maxFrameRate = 0', env['DXVK_CONFIG'])
            self.assertIn('fps_limit=120,fps_limit_method=late', env['MANGOHUD_CONFIG'])
            self.assertEqual(env['LIGHTROOM_OMARCHY_RETAIN_LOUPE'], '1')
            with patch.dict(os.environ, {'LRCC_LIMITER': 'dxvk', 'LRCC_RETAIN_LOUPE': '0'}):
                env = self.app.environment()
                self.assertIn('dxgi.maxFrameRate = 120', env['DXVK_CONFIG'])
                self.assertEqual(env['LIGHTROOM_OMARCHY_RETAIN_LOUPE'], '0')

    def test_runtime_conflict_stops_launch_before_configuration_helpers(self):
        self.app.RUNNER = 'lightroom-omarchy-proton'
        self.app.LR.parent.mkdir(parents=True)
        self.app.LR.touch()
        with patch.object(self.app, 'conflicting_prefix_runtimes', return_value=[123]), \
             patch.object(self.app, 'sync_display_scale') as scale, patch.object(self.app, 'wine') as wine:
            with self.assertRaisesRegex(RuntimeError, 'another runtime'):
                self.app.launch(self.app.LR, 'lightroom', [])
        scale.assert_not_called()
        wine.assert_not_called()

    def test_runtime_switch_guard_uses_live_mappings_and_resolved_prefix(self):
        proc = self.root / 'proc/123'
        proc.mkdir(parents=True)
        self.app.PREFIX.mkdir(parents=True)
        (self.app.PREFIX / 'pfx').symlink_to('.')
        (proc / 'environ').write_bytes(b'WINEPREFIX=' + os.fsencode(self.app.PREFIX / 'pfx') + b'\0')
        maps = proc / 'maps'
        maps.write_text('0-1 r-xp 0 00:00 0 /other/files/lib/wine/x86_64-unix/ntdll.so\n')
        self.assertEqual(self.app.conflicting_prefix_runtimes(proc.parent), [123])
        maps.write_text(f'0-1 r-xp 0 00:00 0 {self.app.RUNTIME}/lib/wine/x86_64-unix/ntdll.so\n')
        self.assertEqual(self.app.conflicting_prefix_runtimes(proc.parent), [])
        maps.write_text('')
        (proc / 'exe').symlink_to('/other/files/bin/wineserver')
        self.assertEqual(self.app.conflicting_prefix_runtimes(proc.parent), [123])
        (proc / 'environ').write_bytes(b'WINEPREFIX=/unrelated\0')
        self.assertEqual(self.app.conflicting_prefix_runtimes(proc.parent), [])

    def test_candidate_retention_default_and_explicit_rollback(self):
        wine = self.app.RUNTIME / 'bin/wine'
        wine.parent.mkdir(parents=True)
        wine.touch()
        self.app.PROTON = True
        self.app.RUNNER = 'lightroom-omarchy-proton'
        (self.app.PREFIX.parent / 'profile.json').write_text(json.dumps({'windows_username': 'test'}))
        (self.app.RUNTIME.parent / 'lightroom-omarchy-proton.json').write_text(json.dumps({
            'recommended_environment': {'LIGHTROOM_OMARCHY_RETAIN_LOUPE': '1'}}))
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(self.app.environment()['LIGHTROOM_OMARCHY_RETAIN_LOUPE'], '1')
            with patch.dict(os.environ, {'LRCC_RETAIN_LOUPE': '0'}):
                self.assertEqual(self.app.environment()['LIGHTROOM_OMARCHY_RETAIN_LOUPE'], '0')
            with patch.dict(os.environ, {'LRCC_RETAIN_LOUPE': 'invalid'}):
                with self.assertRaises(RuntimeError):
                    self.app.environment()

    def test_fractional_scale_and_invalid_scale(self):
        self.assertEqual(self.app.desktop_scale([{"name": "panel", "scale": 1.5, "focused": True}], []), 144)
        with self.assertRaises(RuntimeError):
            self.app.desktop_scale([{"name": "panel", "scale": 0, "focused": True}], [])

    def test_theme_rejects_registry_injection(self):
        palette = {key: "#1a1b26" for key in ("background", "foreground", "accent",
                    "lighter_background", "dark_background", "dark_foreground")}
        registry = self.app.theme_registry(palette)
        self.assertIn('"Menu"="26 27 38"', registry)
        palette['accent'] = '#ffffff"\n[HKEY_CURRENT_USER\\Unrelated]'
        with self.assertRaises(ValueError):
            self.app.theme_registry(palette)

    def test_full_proton_preserves_migrated_identity(self):
        wine = self.app.RUNTIME / "bin/wine"
        wine.parent.mkdir(parents=True)
        wine.touch()
        self.app.PROTON = True
        self.app.RUNNER = "lightroom-omarchy-proton"
        (self.app.PREFIX.parent / "profile.json").write_text(json.dumps({"windows_username": "original-user"}))
        with patch.dict(os.environ, {"LIGHTROOM_OMARCHY_USERNAME": "unrelated-user"}):
            env = self.app.environment()
        self.assertEqual(env["LIGHTROOM_OMARCHY_USERNAME"], "original-user")
        self.assertEqual(env["LIGHTROOM_OMARCHY_CENTER_MENUS"], "1")
        self.assertEqual(env["PROTONPATH"], str(self.app.RUNTIME.parent))
        self.assertIn("dxgi.syncInterval = 0", env["DXVK_CONFIG"])
        self.app.PRESENT_HZ = 120
        with patch.dict(os.environ, {"DXVK_CONFIG": "dxgi.syncInterval = 1"}):
            env = self.app.environment()
        self.assertIn("dxgi.maxFrameRate = 120", env["DXVK_CONFIG"])
        self.assertTrue(env["DXVK_CONFIG"].endswith("dxgi.syncInterval = 1"))
        with patch.dict(os.environ, {"LRCC_PRESENTATION": "upstream"}):
            env = self.app.environment()
        self.assertEqual(env.get("DXVK_CONFIG"), os.environ.get("DXVK_CONFIG"))

    def test_mangohud_limiter_requires_layer_and_avoids_two_caps(self):
        wine = self.app.RUNTIME / "bin/wine"
        wine.parent.mkdir(parents=True)
        wine.touch()
        self.app.PROTON = True
        self.app.RUNNER = "lightroom-omarchy-proton"
        self.app.PRESENT_HZ = 120
        (self.app.PREFIX.parent / "profile.json").write_text(json.dumps({"windows_username": "test"}))
        with patch.dict(os.environ, {"LRCC_LIMITER": "mangohud", "LRCC_PERF": "0"}):
            with self.assertRaisesRegex(RuntimeError, "limiter missing"):
                self.app.environment()
            layer = self.app.DATA / "tools/mangohud/layers/MangoHud.x86_64.json"
            layer.parent.mkdir(parents=True)
            layer.write_text('{}')
            env = self.app.environment()
            self.assertIn("dxgi.maxFrameRate = 0", env["DXVK_CONFIG"])
            self.assertEqual(env["MANGOHUD"], "1")
            self.assertIn("read_cfg=1", env["MANGOHUD_CONFIG"])
            self.assertIn("fps_limit=120,fps_limit_method=late", env["MANGOHUD_CONFIG"])
            self.assertIn("no_display=1", env["MANGOHUD_CONFIG"])
            with patch.dict(os.environ, {"LRCC_PERF": "1"}):
                self.assertNotIn("no_display=1", self.app.environment()["MANGOHUD_CONFIG"])

    def test_dispatch_rejects_hyprland_error_even_on_zero_exit(self):
        with patch.dict(os.environ, {"HYPRLAND_INSTANCE_SIGNATURE": "test", "LRCC_DISPATCHED": "0"}), \
             patch.object(self.app.subprocess, "check_output", return_value="error: invalid rule"):
            with self.assertRaisesRegex(RuntimeError, "rejected"):
                self.app.dispatch_desktop()

    def performance_fixture(self):
        archive = self.root / "graphics.tar.gz"
        with tarfile.open(archive, "w:gz") as t:
            for arch in ("x86_64-windows", "i386-windows"):
                for component, names in (("dxvk", ("dxgi.dll", "d3d11.dll")),
                                         ("vkd3d-proton", ("d3d12.dll", "d3d12core.dll"))):
                    for name in names:
                        member = tarfile.TarInfo(f"bundle/files/lib/wine/{component}/{arch}/{name}")
                        member.size = 2
                        t.addfile(member, io.BytesIO(b"MZ"))
        shcore = self.app.DATA / "patches/shcore.dll"
        shcore.parent.mkdir(parents=True)
        shcore.write_bytes(b"MZ-shcore")
        shcore.with_suffix('.json').write_text(json.dumps({"dll_sha256": self.app.digest(shcore)}))
        for directory in ("system32", "syswow64"):
            (self.app.PREFIX / "drive_c/windows" / directory).mkdir(parents=True)
        prefs = self.app.PREFIX / "drive_c/users/test/AppData/Roaming/Adobe/Lightroom CC/Preferences/Lightroom CC Preferences.agprefs"
        prefs.parent.mkdir(parents=True)
        prefs.write_text('gpu4setting = "auto",\nuseGPUforComputeCB = false,\nuseGPUforDisplayCB = true,\n')
        return archive, prefs

    def test_performance_profile_validates_preferences_before_stopping_or_writing(self):
        archive, prefs = self.performance_fixture()
        prefs.write_text('gpu4setting = "auto",\n')
        with patch.object(self.app, "fetch", return_value=archive), \
             patch.object(self.app, "manifest", return_value={"omarchy-proton": {"filename": "bundle.tar.gz"}}), \
             patch.object(self.app, "run") as execute:
            with self.assertRaisesRegex(RuntimeError, "Missing or ambiguous preference"):
                self.app.repair_performance()
        execute.assert_not_called()
        self.assertFalse((self.app.PREFIX / "drive_c/windows/system32/shcore.dll").exists())

    def test_performance_profile_preserves_first_preferences_backup(self):
        archive, prefs = self.performance_fixture()
        original = prefs.read_text()
        with patch.object(self.app, "fetch", return_value=archive), \
             patch.object(self.app, "manifest", return_value={"omarchy-proton": {"filename": "bundle.tar.gz"}}), \
             patch.object(self.app, "run"), patch.object(self.app, "wine"), \
             patch.object(self.app, "environment", return_value={}), contextlib.redirect_stdout(io.StringIO()):
            self.app.repair_performance()
            self.app.repair_performance()
        self.assertIn('useGPUforComputeCB = true', prefs.read_text())
        backups = list((self.app.DATA / "patches/performance-backups").rglob('*.agprefs'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), original)

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
        self.app.RUNNER = 'lightroom-omarchy-proton'
        with patch.dict(os.environ, {'XDG_DATA_HOME': str(self.root)}), contextlib.redirect_stdout(io.StringIO()):
            self.app.integrate(profile='performance')
        entry = (self.root / 'applications/omarchy-lightroom-cc.desktop').read_text()
        self.assertIn('--profile performance run', entry)

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
