"""Behavioral fixtures; no audit agents, network, compiler, or project execution."""
import argparse
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SKILL = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('scan', SKILL / 'scripts/scan.py')
scan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scan)


class ScanTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'project'
        self.root.mkdir()
        self.bundle = Path(self.temporary.name) / 'bundle'
        self.file('src/vault.vy', '@external\ndef withdraw():\n    pass\n')
        self.directory = self.root / '.vyper-auditor/runs/20260924-120000'
        self.ledger = self.root / '.vyper-auditor/memory.tsv'

    def file(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def prepare(self, passes=1, memory=False, files=None, stamp='20260924-120000'):
        args = argparse.Namespace(root=str(self.root), bundle=str(self.bundle), stamp=stamp,
                                  passes=passes, memory=memory, files=files or [])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            scan.prepare(args)
        return output.getvalue()

    def finding(self, bug='unchecked-transfer', conf=95, title='The vault ignores failed transfers',
                path='src/vault.vy', function='withdraw', agents='1,6', fix=True):
        key = '|'.join(map(scan.normalize, (path, function, bug)))
        body = f'<!--F key={key} conf={conf} kind=FINDING agents={agents}-->\n\n'
        body += f'[{conf}] **{title}**\n\n`{path}.{function}` · Confidence: {conf}\n\n'
        body += '**Description**\nA token can reject a transfer.\n\n**Proof**\nsrc/vault.vy:3; Alice burns 10 shares and receives 0 assets.\n'
        if fix:
            body += '\n**Fix (Option A — validate)**\n\n```diff\n--- a/src/vault.vy\n+++ b/src/vault.vy\n- extcall token.transfer(user, n)\n+ assert extcall token.transfer(user, n)\n```\n'
            body += '\n**Fix (Option B — restrict)**\n\n```diff\n+ assert token == allowed_token\n```\n'
        return body + '\n<!--/F-->\n'

    def lead(self, bug='unchecked-transfer'):
        return (f'<!--F key=src-vault-vy|withdraw|{bug} kind=LEAD agents=3-->\n\n'
                '- **The token may reject transfers** — `src/vault.vy.withdraw` — '
                'Code smells: ignored return — Unverified: token behavior.\n\n<!--/F-->\n')

    def run_file(self, number=1, body=None, agents='12/12'):
        path = self.directory / f'run-{number}.md'
        path.write_text(f'<!--RUN pass={number} agents={agents}-->\n\n' + (self.finding() if body is None else body))
        scan.scope_append(self.directory, **{f'pass_{number}_agents': agents})
        return path

    def merge(self, number=1):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            scan.merge(argparse.Namespace(bundle=str(self.bundle), pass_number=number))
        return out.getvalue()

    def assemble(self):
        result = subprocess.run(['bash', str(SKILL / 'references/assemble.sh'), '--dir', str(self.directory)],
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return (self.directory / 'full-report.md').read_text()

    def terminal(self, file_output=False):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            scan.terminal(argparse.Namespace(dir=str(self.directory), file_output=file_output))
        return output.getvalue()

    def seed(self, rows):
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        self.ledger.write_text(scan.ledger_text({row[0]: row for row in rows}))

    def row(self, key='src-vault-vy|withdraw|unchecked-transfer', kind='FINDING', scans='2'):
        return [key, 'KNOWN', scans, 'abc123', 'Old title', kind]

    def test_plain_scan_does_not_touch_invalid_memory(self):
        self.seed([])
        self.ledger.write_text('corrupt existing memory')
        self.prepare()
        scan.known(argparse.Namespace(bundle=str(self.bundle)))
        self.run_file()
        report = self.assemble()
        self.assertEqual(self.ledger.read_text(), 'corrupt existing memory')
        self.assertNotIn('mem_', (self.directory / 'scope.tsv').read_text())
        for token in ('**Memory**', '**Passes**', 'seen in', 'KNOWN', ' · NEW'):
            self.assertNotIn(token, report)
        self.assertIn('**Compiler context**', report)
        self.assertIn('| **Confidence threshold (1-100)** | 75 |', report)
        self.assertIn('[agents: 1,6]', report)
        self.assertIn('**Proof**', report)
        self.assertIn('--- a/src/vault.vy', report)
        self.assertIn('Fix (Option B', report)
        self.assertEqual(self.terminal(), report)
        self.assertFalse((self.bundle / 'known-findings.md').exists())

    def test_plain_scan_creates_no_ledger(self):
        self.prepare()
        self.run_file(body='')
        self.assemble()
        self.assertFalse(self.ledger.exists())
        with self.assertRaisesRegex(ValueError, 'memory is off'):
            self.merge()

    def test_default_scope_and_explicit_override(self):
        for name in ('lib/dependency.vy', 'tests/test.vy', 'build/contract.vy', 'out/data.vy',
                     '.venv/package.vy', 'src/VaultTest.vy', 'src/x_test.vy', 'interfaces/token.vy'):
            self.file(name, 'pass\n')
        self.file('deploy/create.vy', 'pass\n')
        self.file('src/path with spaces.vy', 'pass\n')
        (self.root / 'src/artifact.vy').mkdir()
        default = scan.discover(self.root, [])
        self.assertEqual(set(default), {'src/vault.vy', 'deploy/create.vy', 'src/path with spaces.vy'})
        self.assertEqual(scan.discover(self.root, ['lib/dependency.vy']), ['lib/dependency.vy'])
        with self.assertRaises(ValueError):
            scan.discover(self.root, ['missing.vy'])
        with self.assertRaises(ValueError):
            scan.discover(self.root, ['src/artifact.vy'])

    def test_spaces_in_paths_survive_scope(self):
        self.file('src/a file.vy', 'pass\n')
        self.prepare()
        self.run_file(body='')
        self.assertIn('`src/a file.vy`', self.assemble())

    def test_path_collision_rejected_before_state(self):
        self.file('src/a_b.vy', 'pass\n')
        self.file('src/a-b.vy', 'pass\n')
        with self.assertRaisesRegex(ValueError, 'identity collision'):
            self.prepare()
        self.assertFalse(self.directory.exists())

    def test_function_collision(self):
        with self.assertRaisesRegex(ValueError, 'identity collision'):
            scan.build_index({'a.vy': 'def a_b():\n    pass\ndef a__b():\n    pass\n'})

    def test_lexer_getters_dunders_and_comments(self):
        source = ('"""def phantom():\n    pass\n"""\n# def fake():\n'
                  'balance: public(\n    uint256\n)\n'
                  '@deploy\ndef __init__():\n    pass\n'
                  '@external\ndef __default__():\n    pass\n')
        functions, uncertain = scan.source_identity(source)
        self.assertFalse(uncertain)
        self.assertEqual(functions, {'balance', '__init__', '__default__', '__module__'})
        self.assertTrue(scan.source_identity('exports: token.__interface__\n')[1])
        self.assertTrue(scan.source_identity('balance: public(\n')[1])

    def test_prune_uses_file_function_pairs(self):
        self.file('src/other.vy', 'def removed():\n    pass\n')
        self.seed([self.row(), self.row('src-vault-vy|removed|bug'), self.row('deleted-vy|withdraw|bug')])
        output = self.prepare(memory=True)
        self.assertIn('Pruned 2 records', output)
        self.assertEqual(len(scan.read_ledger(self.bundle / 'memory-before.tsv')), 1)
        self.assertEqual(len(scan.read_ledger(self.ledger)), 3)
        self.assertEqual(scan.scope_read(self.directory)['mem_before'], '1')

    def test_named_scan_never_prunes(self):
        self.seed([self.row('deleted-vy|withdraw|bug')])
        self.prepare(memory=True, files=['src/vault.vy'])
        self.assertEqual(len(scan.read_ledger(self.bundle / 'memory-before.tsv')), 1)

    def test_exports_and_token_errors_retain_uncertain_records(self):
        self.file('src/vault.vy', 'exports: token.__interface__\n')
        self.seed([self.row()])
        self.prepare(memory=True)
        self.assertEqual(len(scan.read_ledger(self.bundle / 'memory-before.tsv')), 1)

    def test_memory_snapshot_uses_original_source_spelling(self):
        self.file('src/vault.vy', '@deploy\ndef __init__():\n    pass\n')
        self.seed([self.row('src-vault-vy|-init-|bug')])
        self.prepare(memory=True)
        self.run_file(body='')
        self.merge()
        report = self.assemble()
        self.assertIn('`src/vault.vy.__init__`', report)
        self.assertIn('Not re-checked', report)

    def test_bad_ledger_stops_without_artifacts(self):
        for content in ('wrong\n', scan.HEADER + '\nbad\trow\n',
                        scan.HEADER + '\n' + '\t'.join(self.row(scans='0')) + '\n'):
            self.seed([])
            self.ledger.write_text(content)
            with self.assertRaises(ValueError):
                self.prepare(memory=True)
            self.assertEqual(self.ledger.read_text(), content)
            self.assertFalse(self.directory.exists())

    def test_duplicate_ledger_key_rejected(self):
        row = '\t'.join(self.row()) + '\n'
        self.seed([])
        self.ledger.write_text(scan.HEADER + '\n' + row * 2)
        with self.assertRaises(ValueError):
            self.prepare(memory=True)

    def test_single_pass_memory_tags_and_idempotence(self):
        self.seed([self.row()])
        self.prepare(memory=True)
        self.run_file()
        self.assertEqual(self.merge(), '')
        content = self.ledger.read_bytes()
        self.merge()
        self.assertEqual(self.ledger.read_bytes(), content)
        report = self.assemble()
        self.assertIn('KNOWN (3 scans)', report)
        self.assertNotIn('**Passes**', report)
        self.assertNotIn('seen in', report)

    def test_first_scan_empty_known_file_and_stale_removal(self):
        self.prepare(passes=3)
        (self.bundle / 'known-findings.md').write_text('stale')
        scan.known(argparse.Namespace(bundle=str(self.bundle)))
        self.assertFalse((self.bundle / 'known-findings.md').exists())
        self.run_file()
        self.merge()
        scan.known(argparse.Namespace(bundle=str(self.bundle)))
        text = (self.bundle / 'known-findings.md').read_text()
        self.assertIn('unchecked-transfer', text)
        self.assertIn('src/vault.vy.withdraw', text)

    def test_loops_count_scans_once_and_promote_in_place(self):
        self.prepare(passes=3)
        self.run_file(1, self.lead())
        self.merge(1)
        self.run_file(2)
        self.merge(2)
        self.run_file(3, self.finding(title='Later evidence'))
        summary = self.merge(3)
        self.assertIn('no new ground', summary)
        rows = scan.read_ledger(self.ledger)
        self.assertEqual(len(rows), 1)
        row = next(iter(rows.values()))
        self.assertEqual(row[2], '1')
        self.assertEqual(row[5], 'FINDING')
        report = self.assemble()
        self.assertIn('seen in 3/3 runs · NEW', report)
        self.assertIn('Later evidence', report)
        self.assertNotIn('KNOWN', report)

    def test_repeated_scans_increment(self):
        self.prepare(memory=True)
        self.run_file()
        self.merge()
        self.directory = self.root / '.vyper-auditor/runs/20260924-120001'
        self.prepare(memory=True, stamp='20260924-120001')
        self.run_file()
        self.merge()
        self.assertEqual(next(iter(scan.read_ledger(self.ledger).values()))[2], '2')

    def test_ten_passes_sort_numerically_and_choose_later(self):
        self.prepare(passes=10)
        for number in range(1, 11):
            self.run_file(number, self.finding(title=f'Pass {number} evidence'))
            self.merge(number)
        report = self.assemble()
        self.assertIn('Pass 10 evidence', report)
        self.assertIn('seen in 10/10 runs', report)
        self.assertNotIn('Pass 9 evidence', report)

    def test_findings_outrank_leads_across_runs(self):
        self.prepare(passes=2)
        self.run_file(1)
        self.merge(1)
        self.run_file(2, self.lead())
        self.merge(2)
        report = self.assemble()
        self.assertIn('[95]', report)
        self.assertEqual(next(iter(scan.read_ledger(self.ledger).values()))[5], 'LEAD')

    def test_unique_runs_count_not_duplicate_blocks(self):
        self.prepare(passes=2)
        self.run_file(1, self.finding() * 2)
        self.run_file(2, self.finding(conf=90))
        report = self.assemble()
        self.assertIn('seen in 2/2 runs', report)
        self.assertEqual(report.count('**Proof**'), 1)
        self.assertIn('[95]', report)

    def test_partial_agent_loss_on_plain_scan(self):
        self.prepare()
        self.run_file(agents='11/12')
        report = self.assemble()
        self.assertIn('pass 1 ran 11/12 agents', report)
        self.assertNotIn('**Passes**', report)

    def test_total_first_pass_failure_does_not_write_memory(self):
        self.prepare(passes=3)
        scan.scope_append(self.directory, pass_1_failed=1)
        report = self.assemble()
        self.assertIn('0 of 3 (pass 1 failed)', report)
        self.assertIn('This scan reviewed nothing', report)
        self.assertFalse(self.ledger.exists())

    def test_later_failure_keeps_completed_report(self):
        self.prepare(passes=3)
        self.run_file(1, agents='11/12')
        self.merge()
        scan.scope_append(self.directory, pass_2_failed=1)
        report = self.assemble()
        self.assertIn('1 of 3 (pass 1 ran 11/12 agents, pass 2 failed)', report)
        self.assertIn('**Proof**', report)
        self.assertIn(' Seen |', self._large_failed_scan())

    def _large_failed_scan(self):
        self.run_file(1, ''.join(self.finding(bug=f'bug-{i}') for i in range(21)))
        self.assemble()
        return self.terminal()

    def test_malformed_blocks_visible_and_ledger_unchanged(self):
        self.seed([self.row()])
        self.prepare(memory=True)
        original = self.ledger.read_bytes()
        self.run_file(body=self.finding() + self.finding(bug='other').replace('<!--/F-->', ''))
        with self.assertRaisesRegex(ValueError, 'ledger unchanged'):
            self.merge()
        self.assertEqual(self.ledger.read_bytes(), original)
        report = self.assemble()
        self.assertIn('unclosed finding', report)
        self.assertEqual(report.count('**Proof**'), 1)

    def test_malformed_marker_field_is_not_silent(self):
        self.prepare()
        self.run_file(body=self.finding().replace('conf=95', 'conf=oops'))
        report = self.assemble()
        self.assertIn('invalid F marker', report)
        self.assertIn('None — this scan raised no findings', report)

    def test_atomic_failure_preserves_original(self):
        self.seed([self.row()])
        self.prepare(memory=True)
        self.run_file()
        before = self.ledger.read_bytes()
        with patch.object(scan.os, 'replace', side_effect=OSError('simulated interrupted replace')):
            with self.assertRaises(OSError):
                self.merge()
        self.assertEqual(self.ledger.read_bytes(), before)
        self.assertTrue(self.ledger.with_name('memory.tsv.tmp').exists())
        self.merge()
        self.assertFalse(self.ledger.with_name('memory.tsv.tmp').exists())

    def test_threshold_and_partial_promotion_preserve_proof(self):
        self.prepare()
        self.run_file(body=self.finding('partial', 75, fix=False) + self.finding('low', 74, fix=False)
                      + self.finding('promoted', 75))
        report = self.assemble()
        self.assertIn('Below Confidence Threshold', report)
        self.assertEqual(report.count('**Proof**'), 3)
        self.assertEqual(report.count('Fix (Option A'), 1)

    def test_twenty_findings_and_many_leads_print_full(self):
        self.prepare()
        self.run_file(body=''.join(self.finding(bug=f'bug-{i}') for i in range(20))
                      + ''.join(self.lead(f'lead-{i}') for i in range(40)))
        report = self.assemble()
        self.assertEqual(self.terminal(), report)
        self.assertEqual(report.count('**Proof**'), 20)

    def test_twenty_one_findings_abbreviates_and_copy_is_exact(self):
        self.prepare()
        self.run_file(body=''.join(self.finding(bug=f'bug-{i}') for i in range(21)))
        report = self.assemble()
        terminal = self.terminal(file_output=True)
        self.assertIn('top 3 of 21', terminal)
        self.assertNotIn('**Proof**', terminal)
        self.assertNotIn(' Seen |', terminal)
        copy = self.root / 'project-pashov-ai-vyper-audit-report-20260924-120000.md'
        self.assertEqual(copy.read_bytes(), (self.directory / 'full-report.md').read_bytes())
        self.assertIn(str(copy), terminal)
        self.assertNotIn(str(self.directory / 'full-report.md'), terminal)
        self.assertEqual(report.count('**Proof**'), 21)

    def test_stamp_collision_does_not_overwrite(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self.prepare()

    def test_source_is_frozen_after_prepare(self):
        self.prepare()
        initial = (self.bundle / 'source.md').read_bytes()
        self.file('src/vault.vy', 'new source\n')
        scan.known(argparse.Namespace(bundle=str(self.bundle)))
        self.assertEqual((self.bundle / 'source.md').read_bytes(), initial)

    def test_no_source_stops_before_state(self):
        (self.root / 'src/vault.vy').unlink()
        with self.assertRaisesRegex(ValueError, 'No in-scope'):
            self.prepare()
        self.assertFalse(self.directory.exists())

    def test_missing_git_is_supported(self):
        original_run = scan.subprocess.run
        def without_git(command, **kwargs):
            if command[0] == 'git':
                raise FileNotFoundError('git')
            return original_run(command, **kwargs)
        with patch.object(scan.subprocess, 'run', side_effect=without_git):
            self.prepare(memory=True)
        self.assertEqual(scan.load_state(self.bundle)['sha'], 'none')

    def test_project_path_with_spaces(self):
        old_root = self.root
        self.root = old_root.with_name('project with spaces')
        old_root.rename(self.root)
        self.directory = self.root / '.vyper-auditor/runs/20260924-120000'
        self.ledger = self.root / '.vyper-auditor/memory.tsv'
        self.prepare(passes=2)
        self.run_file(1)
        self.run_file(2)
        report = self.assemble()
        self.assertIn('seen in 2/2 runs', report)
        self.assertEqual(report.count('**Proof**'), 1)

    def test_missing_memory_input_is_visible(self):
        self.prepare(memory=True)
        self.run_file()
        (self.directory / 'memory-before.tsv').unlink()
        report = self.assemble()
        self.assertIn('Memory inputs missing', report)
        self.assertNotIn(' · NEW', report)

    def test_memory_write_error_does_not_claim_persisted_tag(self):
        self.seed([self.row()])
        self.prepare(memory=True)
        self.run_file()
        scan.scope_append(self.directory, memory_error='simulated write failure')
        report = self.assemble()
        self.assertIn('**Memory error**', report)
        self.assertNotIn('KNOWN (3 scans)', report)

    def test_stale_temporary_ledger_warns(self):
        self.seed([self.row()])
        self.ledger.with_name('memory.tsv.tmp').write_text('unfinished')
        warning = io.StringIO()
        with contextlib.redirect_stderr(warning):
            self.prepare(memory=True)
        self.assertIn('unfinished scan', warning.getvalue())
        self.run_file()
        self.merge()
        self.assertFalse(self.ledger.with_name('memory.tsv.tmp').exists())

    def test_getters_and_dunders_survive_pruning(self):
        self.file('src/vault.vy', 'balance: public(uint256)\ndef __init__():\n    pass\ndef __default__():\n    pass\n')
        self.seed([self.row(f'src-vault-vy|{scan.normalize(function)}|bug')
                   for function in ('balance', '__init__', '__default__', '__module__')])
        self.prepare(memory=True)
        self.assertEqual(len(scan.read_ledger(self.bundle / 'memory-before.tsv')), 4)

    def test_same_named_functions_in_different_files_stay_separate(self):
        self.file('src/other.vy', 'def withdraw():\n    pass\n')
        self.prepare()
        self.run_file(body=self.finding() + self.finding(path='src/other.vy'))
        report = self.assemble()
        self.assertEqual(report.count('**Proof**'), 2)
        self.assertIn('`src/other.vy.withdraw`', report)
        self.assertIn('`src/vault.vy.withdraw`', report)

    def test_merge_pass_order_is_enforced(self):
        self.prepare(passes=3)
        self.run_file(2)
        with self.assertRaisesRegex(ValueError, 'in order'):
            self.merge(2)
        self.assertFalse(self.ledger.exists())

    def test_cli_invalid_pass_count(self):
        result = subprocess.run(['python3', str(SKILL / 'scripts/scan.py'), 'prepare',
                                 '--bundle', str(self.bundle), '--stamp', '20260924-120000', '--passes', '11'],
                                capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.bundle.exists())


if __name__ == '__main__':
    unittest.main()
