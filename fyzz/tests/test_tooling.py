"""Behavior checks for portable helpers; no blockchain dependencies required."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'fyzz.py'
spec = importlib.util.spec_from_file_location('fyzz_tool', SCRIPT)
fyzz = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fyzz)


class ToolingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'src').mkdir()
        (self.root / 'src' / 'Counter.vy').write_text('count: public(uint256)\n')
        (self.root / 'moccasin.toml').write_text('[project]\n')

    def tearDown(self):
        self.temp.cleanup()

    def cli(self, command, *flags, ok=True):
        result = subprocess.run([sys.executable, str(SCRIPT), command, str(self.root), *flags], text=True, capture_output=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        return result

    def artifact(self, name='inc'):
        path = self.root / 'artifact.json'
        path.write_text(json.dumps({'contractName': 'Counter', 'sourceName': 'src/Counter.vy', 'abi': [
            {'type': 'function', 'name': name, 'stateMutability': 'nonpayable', 'inputs': [{'name': 'n', 'type': 'uint256'}], 'outputs': []}]}))
        return str(path)

    def test_scaffold_paths_and_no_overwrite(self):
        self.cli('scaffold', '--suite-dir', 'checks/fuzz', '--meta-dir', 'data/fuzz')
        self.assertTrue((self.root / 'checks/fuzz/test_stateful.py').exists())
        conf = (self.root / 'checks/fuzz/conftest.py').read_text()
        self.assertNotIn('__FYZZ_META_REL__', conf)
        self.cli('scaffold', '--suite-dir', 'checks/fuzz', '--meta-dir', 'data/fuzz', ok=False)
        self.cli('scaffold', '--suite-dir', '../escape', ok=False)
        self.cli('scaffold', '--suite-dir', 'fuzz_data/nested', ok=False)

    def test_framework_ambiguity(self):
        self.assertEqual(fyzz.framework(self.root, 'auto', {}), 'moccasin')
        (self.root / 'ape-config.yaml').write_text('name: demo\n')
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            fyzz.framework(self.root, 'auto', {})
        self.assertEqual(fyzz.framework(self.root, 'ape', {}), 'ape')

    def test_snapshot_and_drift_are_read_only(self):
        self.cli('scaffold')
        self.cli('inventory', '--artifact', self.artifact())
        self.cli('snapshot')
        baseline = (self.root / 'fuzz_data/last-run.json').read_bytes()
        clean = self.cli('diff')
        self.assertFalse(clean['sources']['changed'])
        (self.root / 'src/Counter.vy').write_text('count: public(uint256)\n# semantic edit\n')
        self.assertEqual(self.cli('diff')['sources']['changed'], ['src/Counter.vy'])
        self.cli('inventory', '--artifact', self.artifact('decrement'))
        self.assertEqual(self.cli('diff')['signatures']['changed'], ['src/Counter.vy:Counter'])
        self.assertEqual((self.root / 'fuzz_data/last-run.json').read_bytes(), baseline)
        self.cli('snapshot', ok=False)
        self.cli('snapshot', '--refresh')
        self.assertFalse(self.cli('diff')['sources']['changed'])

    def test_property_reconciliation(self):
        self.cli('scaffold')
        meta = self.root / 'fuzz_data'
        (meta / 'PROPERTIES.md').write_text('- [x] **GL-01** — conserved\n- [ ] **SP-01** — increases\n- [~] **GL-02** — stale\n')
        props = self.cli('properties')
        self.assertTrue(props['GL-01']['drift'])
        code = 'def conserved():\n    """fyzz: GL-01 conservation"""\n    assert True\n'
        (self.root / 'test/fuzz/properties.py').write_text(code)
        props = self.cli('properties')
        self.assertFalse(props['GL-01']['drift'])
        self.assertEqual(props['GL-02']['state'], '~')
        (self.root / 'test/fuzz/duplicate.py').write_text(code)
        self.assertTrue(self.cli('properties')['GL-01']['drift'])

    def test_sync_tracks_add_remove_specs_and_handwritten_actions(self):
        self.cli('scaffold')
        self.cli('inventory', '--artifact', self.artifact())
        meta = self.root / 'fuzz_data'
        spec = meta / 'PROPERTIES.md'
        spec.write_text('- [ ] **GL-01** — balance\n  Dependencies: Counter.add\n')
        self.cli('snapshot')
        spec.write_text('- [ ] **GL-01** — balance\n  Dependencies: Counter.remove\n')
        self.assertEqual(self.cli('diff')['properties']['changed'], ['GL-01'])
        new = self.root / 'src/Added.vy'
        new.write_text('value: public(uint256)\n')
        self.assertEqual(self.cli('diff')['sources']['added'], ['src/Added.vy'])
        (self.root / 'src/Counter.vy').unlink()
        self.assertEqual(self.cli('diff')['sources']['removed'], ['src/Counter.vy'])
        actions = self.root / 'test/fuzz/actions.py'
        handwritten = actions.read_text() + '\n# handwritten strategy customization\n'
        actions.write_text(handwritten)
        self.assertIn('actions.py', self.cli('diff')['suite_hashes']['changed'])
        self.assertEqual(actions.read_text(), handwritten)

    def test_campaign_exit_and_timeout(self):
        self.cli('scaffold')
        runner = json.dumps([sys.executable, '-c', 'import sys; sys.exit(0)'])
        self.assertTrue(self.cli('run', '--runner', runner)['passed'])
        fail = json.dumps([sys.executable, '-c', 'import sys; sys.exit(7)'])
        result = self.cli('run', '--runner', fail, ok=False)
        self.assertEqual(json.loads(result.stdout)['exit_code'], 7)
        sleep = json.dumps([sys.executable, '-c', 'import time; time.sleep(10)'])
        result = self.cli('run', '--runner', sleep, '--timeout', '1', ok=False)
        self.assertEqual(json.loads(result.stdout)['status'], 'timeout')

    def test_inventory_requires_real_artifacts(self):
        self.cli('inventory', ok=False)
        result = self.cli('inventory', '--artifact', self.artifact())
        self.assertEqual(result['contracts'], 1)
        data = json.loads((self.root / 'fuzz_data/contracts.json').read_text())
        self.assertEqual(data['contracts'][0]['functions'][0]['signature'], 'inc(uint256)')


if __name__ == '__main__':
    unittest.main()
