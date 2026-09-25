"""Opt-in native runner tests. Set FYZZ_APE_PYTHON / FYZZ_MOCCASIN_PYTHON.

Install hypothesis, pytest and the relevant framework (+ ape-vyper for Ape) in
separate environments. These tests generate actual suites in temporary projects.
"""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/fyzz.py'
CONTRACT = '''#pragma version ^0.4.0
count: public(uint256)

@external
def add(amount: uint256):
    self.count += amount + BUG
'''
ACTIONS = '''from hypothesis.stateful import rule
from hypothesis import strategies as st

class Actions:
    @rule(amount=st.integers(min_value=1, max_value=5))
    def add(self, amount):
        with self.diagnostics.action("add", inputs={"amount": amount}, transition="increase"):
            CALL
            self.model.balances["count"] = self.model.balances.get("count", 0) + amount
'''
PROPERTIES = '''from hypothesis.stateful import invariant

class Properties:
    @invariant()
    def count(self):
        """fyzz: GL-01"""
        def check():
            assert self.deployment.count() == self.model.balances.get("count", 0), "GL-01"
        self.diagnostics.check("GL-01", check)
'''


@pytest.mark.parametrize('framework', ['ape', 'moccasin'])
def test_native_campaign_shrink_and_repro(tmp_path, framework):
    python = os.environ.get('FYZZ_' + framework.upper() + '_PYTHON')
    if not python:
        pytest.skip(f'Set FYZZ_{framework.upper()}_PYTHON for actual framework test')
    env = dict(os.environ, PATH=str(Path(python).parent) + os.pathsep + os.environ['PATH'])
    root = tmp_path / framework
    root.mkdir()
    folder = root / ('contracts' if framework == 'ape' else 'src')
    folder.mkdir()
    contract = folder / 'Counter.vy'
    if framework == 'ape':
        (root / 'ape-config.yaml').write_text('name: fyzz-validation\nvyper:\n  version: 0.4.3\n')
        setup = '''from ape import project, accounts

def deploy(config):
    c = accounts.test_accounts[0].deploy(project.Counter)
    assert c.count() == 0
    return c
'''
        call = 'self.deployment.add(amount, sender=__import__("ape").accounts.test_accounts[0])'
        runner = [str(Path(python).parent / 'ape'), 'test']
    else:
        (root / 'moccasin.toml').write_text('[project]\nsrc = "src"\n')
        setup = '''from src import Counter

def deploy(config):
    c = Counter.deploy()
    assert c.count() == 0
    return c
'''
        call = 'self.deployment.add(amount)'
        runner = [str(Path(python).parent / 'mox'), 'test', '--no-install']
    result = subprocess.run([python, str(SCRIPT), 'scaffold', str(root), '--framework', framework], text=True, capture_output=True, env=env)
    assert result.returncode == 0, result.stderr
    suite = root / 'test/fuzz'
    (suite / 'setup.py').write_text(setup)
    (suite / 'actions.py').write_text(ACTIONS.replace('CALL', call))
    (suite / 'properties.py').write_text(PROPERTIES)
    for bug in [0, 1]:
        contract.write_text(CONTRACT.replace('BUG', str(bug)))
        result = subprocess.run([python, str(SCRIPT), 'run', str(root), '--profile', 'smoke', '--timeout', '120', '--runner', json.dumps(runner)], text=True, capture_output=True, env=env)
        assert result.stdout, result.stderr
        report = json.loads(result.stdout)
        log = Path(report['log']).read_text()
        assert report['status'] == 'completed', log
        assert report['passed'] is (not bug), log
        if bug:
            assert 'GL-01' in log and ('Falsifying example' in log or 'Failing test case' in log), log
            traces = [json.loads(p.read_text()) for p in (Path(report['log']).parent / 'traces').glob('*.json')]
            shortest = min((t for t in traces if t['failure'].get('spec_id') == 'GL-01'), key=lambda t: len(t['actions']))
            assert len(shortest['actions']) == 1
            amount = shortest['actions'][0]['inputs']['amount']
            assert amount == 1
            (suite / 'test_repro.py').write_text('''from .runtime import isolation

def test_repro_GL_01(fyzz_config, fyzz_deploy):
    with isolation(fyzz_config["framework"]):
        contract = fyzz_deploy()
        REPLAY
        assert contract.count() == AMOUNT, "GL-01"
'''.replace('REPLAY', call.replace('self.deployment', 'contract').replace('amount', str(amount))).replace('AMOUNT', str(amount)))
            repro = subprocess.run(runner + [str(suite / 'test_repro.py'), '-q'], cwd=root, text=True, capture_output=True, env=env)
            assert repro.returncode == 1 and 'GL-01' in repro.stdout, repro.stdout + repro.stderr
