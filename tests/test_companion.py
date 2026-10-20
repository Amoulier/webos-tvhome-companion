import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(ROOT / path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

watch = load('watch', 'tv/watch.py')
catalog = load('catalog', 'tv/sync-apps.py')

class WakeTests(unittest.TestCase):
    def test_initial_active_opens_home(self):
        self.assertTrue(watch.is_wake(None, 'Active'))

    def test_stable_active_does_not_reopen(self):
        self.assertFalse(watch.is_wake('Active', 'Active'))

    def test_resume_when_state_did_not_change(self):
        self.assertTrue(watch.is_wake('Active', 'Active', gap=16))

    def test_standby_and_unknown_do_not_launch(self):
        self.assertFalse(watch.is_wake('Active', 'Suspend', gap=16))
        self.assertFalse(watch.is_wake('Active', None, gap=16))

    def test_recovery_only_targets_stock_inputs(self):
        self.assertTrue(watch.is_stock_input('com.webos.app.hdmi2'))
        self.assertTrue(watch.is_stock_input('com.webos.app.home'))
        self.assertFalse(watch.is_stock_input('org.xbmc.kodi'))
        self.assertFalse(watch.is_stock_input('netflix'))

class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        (self.base / 'icons').mkdir()
        self.original = 'window.TV_APPS={apps:[],inputs:[{appId:"hdmi2",label:"HDMI 2"}]};\n'
        (self.base / 'apps.js').write_text(self.original)
        self.base_patch = patch.object(catalog, 'BASE', str(self.base))
        self.base_patch.start()
        self.addCleanup(self.base_patch.stop)
        self.addCleanup(self.temp.cleanup)

    def luna(self, method, payload=None):
        if method == 'listLaunchPoints':
            return {'returnValue': True, 'launchPoints': self.points}
        if method == 'getForegroundAppInfo':
            return {'appId': self.front}
        return {'returnValue': True}

    def run_sync(self, front='org.xbmc.kodi', dry=False):
        self.front = front
        with patch.object(catalog, 'luna', side_effect=self.luna) as luna:
            with patch.object(catalog.subprocess, 'check_output', return_value=b'{"returnValue":true}') as kill:
                catalog.sync(dry_run=dry)
        return luna, kill

    def test_missing_icon_does_not_hide_installed_app(self):
        self.points = [{'id': 'org.xbmc.kodi', 'title': 'Kodi', 'icon': '/missing/icon.png'}]
        luna, kill = self.run_sync()
        text = (self.base / 'apps.js').read_text()
        self.assertIn('org.xbmc.kodi', text)
        self.assertIn('"icon": "icon.png"', text)
        self.assertIn('inputs":[{appId:"hdmi2",label:"HDMI 2"}]', text)
        self.assertFalse(any(c.args[0] == 'launch' for c in luna.call_args_list))
        self.assertIn('luna://com.palm.webappmanager/killApp', kill.call_args.args[0])

    def test_hidden_and_removed_apps_are_not_retained(self):
        self.points = [{'id': 'current', 'title': 'Current'}, {'id': 'hidden', 'hidden': True}]
        self.run_sync()
        text = (self.base / 'apps.js').read_text()
        self.assertIn('current', text)
        self.assertNotIn('"id": "hidden"', text)

    def test_empty_or_failed_inventory_keeps_old_catalog(self):
        self.points = []
        self.run_sync()
        self.assertEqual((self.base / 'apps.js').read_text(), self.original)

    def test_unchanged_catalog_does_not_restart_home(self):
        self.points = [{'id': 'current'}]
        self.run_sync()
        luna, kill = self.run_sync()
        kill.assert_not_called()
        self.assertEqual(len(luna.call_args_list), 1)

    def test_reload_only_brings_home_forward_if_already_foreground(self):
        self.points = [{'id': 'current'}]
        luna, kill = self.run_sync(front='com.gathin.tvhome')
        self.assertTrue(any(c.args[0] == 'launch' for c in luna.call_args_list))

    def test_dry_run_does_not_copy_icon_write_catalog_or_restart(self):
        icon = self.base / 'source.png'
        icon.write_bytes(b'example-icon')
        self.points = [{'id': 'new', 'title': 'New', 'icon': str(icon)}]
        luna, kill = self.run_sync(dry=True)
        self.assertEqual((self.base / 'apps.js').read_text(), self.original)
        self.assertEqual(list((self.base / 'icons').iterdir()), [])
        kill.assert_not_called()

if __name__ == '__main__':
    unittest.main()
