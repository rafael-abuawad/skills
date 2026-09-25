#!/usr/bin/env python3
"""Portable Fyzz artifact tooling. Protocol semantics remain agent-authored."""
import argparse
from collections import Counter
import ast
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

VERSION = 1
PROFILES = {"smoke": (10, 20), "standard": (100, 50), "extended": (1000, 100)}


def read(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    temp.replace(path)


def inside(root, value):
    path = (root / value).resolve()
    if path == root or not path.is_relative_to(root):
        raise ValueError(f'Output must be a subdirectory of project: {value}')
    return path


def paths(args):
    root = Path(args.project).resolve()
    if not root.is_dir():
        raise ValueError(f'Project does not exist: {root}')
    meta = inside(root, args.meta_dir or 'fuzz_data')
    saved = read(meta / 'fyzz.json', {})
    suite = inside(root, args.suite_dir or saved.get('suite_dir', 'test/fuzz'))
    if suite == meta or suite.is_relative_to(meta) or meta.is_relative_to(suite):
        raise ValueError('Suite and metadata directories must not overlap')
    return root, suite, meta, saved


def sources(root, suite, meta):
    excluded = {'.git', '.venv', 'venv', 'node_modules', 'build', '.cache'}
    return sorted(p for p in root.rglob('*.vy') if not excluded.intersection(p.relative_to(root).parts)
                  and not p.is_relative_to(suite) and not p.is_relative_to(meta))


def framework(root, explicit, saved):
    if explicit != 'auto':
        return explicit
    if saved.get('framework'):
        return saved['framework']
    candidates = set()
    if (root / 'moccasin.toml').exists():
        candidates.add('moccasin')
    if any((root / p).exists() for p in ('ape-config.yaml', 'ape-config.yml')):
        candidates.add('ape')
    text = (root / 'pyproject.toml').read_text() if (root / 'pyproject.toml').exists() else ''
    if '[tool.moccasin' in text:
        candidates.add('moccasin')
    if '[tool.ape' in text:
        candidates.add('ape')
    # Boa is also a Moccasin dependency; do not treat that alone as ambiguity.
    if not candidates:
        tests = list(root.glob('test*/**/*.py'))
        if 'titanoboa' in text or any(re.search(r'^\s*(import boa|from boa\b)', p.read_text(), re.M) for p in tests):
            candidates.add('boa')
    if len(candidates) != 1:
        raise ValueError(f'Framework ambiguous or absent ({sorted(candidates)}); specify --framework')
    return candidates.pop()


def versions():
    result = {'python': sys.version.split()[0]}
    for name in ('hypothesis', 'pytest', 'titanoboa', 'eth-ape', 'ape-vyper', 'moccasin', 'vyper'):
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = None
    return result


def inspect(args, root, suite, meta, saved):
    fw = framework(root, args.framework, saved)
    modules = ['hypothesis', 'pytest', {'boa': 'boa', 'ape': 'ape', 'moccasin': 'moccasin'}[fw]]
    if fw == 'ape':
        modules.append('ape_vyper')
    missing = [m for m in modules if importlib.util.find_spec(m) is None]
    return {'framework': fw, 'versions': versions(), 'missing_modules': missing,
            'sources': [str(p.relative_to(root)) for p in sources(root, suite, meta)],
            'python': sys.executable, 'ready': not missing}


def abi_type(item):
    value = item['type']
    if value.startswith('tuple'):
        return '(' + ','.join(abi_type(c) for c in item['components']) + ')' + value[5:]
    return value


def inventory(args, root, suite, meta, saved):
    if not args.artifact:
        raise ValueError('Supply compiler artifacts with --artifact; source regex is not an ABI extractor')
    contracts = []
    for path in args.artifact:
        p = (root / path).resolve()
        obj = read(p)
        if not isinstance(obj, dict) or not isinstance(obj.get('abi'), list):
            raise ValueError(f'{p}: expected object with abi, contract/contractName and source/sourceName')
        name = obj.get('contract') or obj.get('contractName')
        source = obj.get('source') or obj.get('sourceName')
        if not name or not isinstance(source, str) or not (root / source).is_file():
            raise ValueError(f'{p}: explicit contract name and existing source path required')
        src = (root / source).resolve()
        if not src.is_relative_to(root) or src.suffix != '.vy':
            raise ValueError(f'{p}: source must be a project Vyper file')
        functions = []
        for item in obj['abi']:
            if item.get('type') == 'function':
                functions.append({**item, 'signature': item['name'] + '(' + ','.join(abi_type(x) for x in item['inputs']) + ')'})
        contracts.append({'contract': name, 'source': str(src.relative_to(root)), 'abi': obj['abi'], 'functions': functions})
    keys = [(c['source'], c['contract']) for c in contracts]
    if len(set(keys)) != len(keys):
        raise ValueError('Duplicate contract identities')
    write(meta / 'contracts.json', {'schema_version': VERSION, 'contracts': contracts})
    return {'contracts': len(contracts), 'path': str(meta / 'contracts.json')}


def scaffold(args, root, suite, meta, saved):
    fw = framework(root, args.framework, saved)
    assets = Path(__file__).resolve().parents[1] / 'assets' / 'suite'
    files = [p for p in assets.iterdir() if p.is_file() and p.suffix == '.py']
    if not files:
        raise ValueError('Suite assets are missing')
    targets = [suite / p.name for p in files] + [meta / 'fyzz.json', meta / 'PROPERTIES.md', meta / 'profiles.json']
    occupied = [str(p) for p in targets if p.exists()]
    if occupied:
        raise ValueError('Refusing to overwrite existing artifacts: ' + ', '.join(occupied))
    suite.mkdir(parents=True, exist_ok=True)
    meta.mkdir(parents=True, exist_ok=True)
    for p in files:
        (suite / p.name).write_text(p.read_text().replace('__FYZZ_META_REL__', os.path.relpath(meta, suite)))
    write(meta / 'fyzz.json', {'schema_version': VERSION, 'framework': fw,
          'suite_dir': str(suite.relative_to(root)), 'meta_dir': str(meta.relative_to(root)), 'versions': versions()})
    write(meta / 'profiles.json', {k: {'max_examples': v[0], 'stateful_step_count': v[1]} for k, v in PROFILES.items()})
    (meta / 'PROPERTIES.md').write_text('# Fyzz properties\n\nUse stable GL-NN / SP-NN IDs, evidence and Guarantee tags.\n')
    return {'suite': str(suite), 'metadata': str(meta), 'status': 'requires protocol-specific implementation'}


def property_map(suite, meta):
    spec = meta / 'PROPERTIES.md'
    entries = {}
    if spec.exists():
        for state, ident, body in re.findall(r'^- \[([ x~\-])\]\s+\*\*((?:GL|SP)-\d+)\*\*(.*?)(?=^- \[|\Z)', spec.read_text(), re.M | re.S):
            if ident in entries:
                raise ValueError(f'Duplicate property ID: {ident}')
            entries[ident] = {'state': state, 'spec': body, 'implementations': []}
    for path in sorted(suite.rglob('*.py')) if suite.exists() else []:
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = ast.get_docstring(node) or ''
                match = re.match(r'fyzz: ((?:GL|SP)-\d+)\b', doc)
                if match:
                    ident = match[1]
                    entries.setdefault(ident, {'state': None, 'spec': None, 'implementations': []})['implementations'].append(
                        {'file': str(path.relative_to(suite)), 'function': node.name, 'line': node.lineno})
    for entry in entries.values():
        count = len(entry['implementations'])
        entry['drift'] = count > 1 or (entry['state'] == 'x' and not count) or entry['state'] is None
    return entries


def snapshot_data(root, suite, meta, saved):
    inv = read(meta / 'contracts.json', {'contracts': []})
    return {'schema_version': VERSION, 'config': saved, 'versions': versions(),
            'sources': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources(root, suite, meta)},
            'signatures': {c['source'] + ':' + c['contract']: sorted(f['signature'] for f in c['functions']) for c in inv['contracts']},
            'properties': property_map(suite, meta),
            'suite_hashes': {str(p.relative_to(suite)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(suite.rglob('*.py'))},
            'selection': read(meta / 'selection.json', {}),
            'property_plan_hash': hashlib.sha256((meta / 'property-plan.md').read_bytes()).hexdigest() if (meta / 'property-plan.md').exists() else None}


def delta(old, new):
    return {'added': sorted(new.keys() - old.keys()), 'removed': sorted(old.keys() - new.keys()),
            'changed': sorted(k for k in old.keys() & new.keys() if old[k] != new[k])}


def run(args, root, suite, meta, saved):
    fw = framework(root, args.framework, saved)
    runner = json.loads(args.runner) if args.runner else {'boa': [sys.executable, '-m', 'pytest'], 'ape': ['ape', 'test'], 'moccasin': ['mox', 'test']}[fw]
    if not isinstance(runner, list) or not runner or not all(isinstance(x, str) for x in runner):
        raise ValueError('--runner must be a nonempty JSON argv array')
    if not suite.is_dir():
        raise ValueError('Suite missing; scaffold and implement it first')
    command = runner + [str(suite), '-v']
    meta.mkdir(parents=True, exist_ok=True)
    run_dir = meta / 'runs' / (time.strftime('%Y%m%dT%H%M%S') + '-' + str(time.time_ns()))
    run_dir.mkdir(parents=True)
    env = dict(os.environ, FYZZ_PROFILE=args.profile, FYZZ_META_DIR=str(meta), FYZZ_RUN_DIR=str(run_dir),
               HYPOTHESIS_STORAGE_DIRECTORY=str(meta / 'hypothesis'), PYTEST_ADDOPTS=os.environ.get('PYTEST_ADDOPTS', '') + ' -o cache_dir=' + str(meta / 'pytest-cache'))
    if args.max_examples is not None:
        env['FYZZ_MAX_EXAMPLES'] = str(args.max_examples)
    if args.steps is not None:
        env['FYZZ_STEPS'] = str(args.steps)
    if args.seed is not None:
        command += ['--hypothesis-seed', str(args.seed)]
    start = time.monotonic()
    with (run_dir / 'campaign.log').open('w') as log:
        proc = subprocess.Popen(command, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        status = 'completed'
        try:
            code = proc.wait(timeout=args.timeout)
        except (subprocess.TimeoutExpired, KeyboardInterrupt) as error:
            status = 'timeout' if isinstance(error, subprocess.TimeoutExpired) else 'interrupted'
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
            code = proc.returncode
    counts, transitions = Counter(), Counter()
    diagnostics_errors = []
    examples_recorded = 0
    for path in (run_dir / 'reachability').glob('*.json'):
        try:
            record = read(path)
            counts.update(record['counts'])
            transitions.update(record['transitions'])
            examples_recorded += 1
        except (ValueError, KeyError, TypeError) as error:
            diagnostics_errors.append(f'{path.name}: {error}')
    write(run_dir / 'reachability-summary.json', {'counts': dict(counts), 'transitions': dict(transitions),
          'examples_recorded': examples_recorded, 'includes_shrinking_and_replay': True, 'errors': diagnostics_errors})
    result = {'status': status, 'exit_code': code, 'passed': status == 'completed' and code == 0,
              'seconds': round(time.monotonic() - start, 2), 'command': command, 'profile': args.profile,
              'launcher_versions': versions(), 'effective_settings': read(run_dir / 'effective-settings.json'),
              'log': str(run_dir / 'campaign.log')}
    write(run_dir / 'result.json', result)
    return result


def positive(value):
    value = int(value)
    if value <= 0:
        raise argparse.ArgumentTypeError('must be positive')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['inspect', 'inventory', 'scaffold', 'run', 'snapshot', 'diff', 'properties'])
    parser.add_argument('project')
    parser.add_argument('--suite-dir')
    parser.add_argument('--meta-dir')
    parser.add_argument('--framework', choices=['auto', 'ape', 'boa', 'moccasin'], default='auto')
    parser.add_argument('--artifact', action='append')
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--runner')
    parser.add_argument('--profile', choices=PROFILES, default='standard')
    parser.add_argument('--timeout', type=positive)
    parser.add_argument('--max-examples', type=positive)
    parser.add_argument('--steps', type=positive)
    parser.add_argument('--seed', type=int)
    args = parser.parse_args()
    try:
        root, suite, meta, saved = paths(args)
        if args.command in ('inspect', 'inventory', 'scaffold', 'run'):
            result = globals()[args.command](args, root, suite, meta, saved)
        elif args.command == 'properties':
            result = property_map(suite, meta)
        else:
            current = snapshot_data(root, suite, meta, saved)
            baseline = meta / 'last-run.json'
            if args.command == 'snapshot':
                if not saved or not (meta / 'contracts.json').exists():
                    raise ValueError('Configuration and inventory required before snapshot')
                if baseline.exists() and not args.refresh:
                    raise ValueError('Snapshot exists; use --refresh after validation')
                write(baseline, current)
                result = {'snapshot': str(baseline)}
            else:
                previous = read(baseline)
                if previous is None:
                    raise ValueError('Snapshot missing; run Fyzz and validate before snapshot')
                result = {key: delta(previous.get(key, {}), current[key]) for key in ('sources', 'signatures', 'properties', 'suite_hashes')}
                result['versions'] = delta(previous.get('versions', {}), current['versions'])
                result['config_changed'] = previous.get('config') != current['config']
                result['selection_changed'] = previous.get('selection') != current['selection']
                result['property_plan_changed'] = previous.get('property_plan_hash') != current['property_plan_hash']
                result['inventory_note'] = 'Recompile and refresh contracts.json before interpreting signature drift.'
        print(json.dumps(result, indent=2))
        if args.command == 'run' and not result['passed']:
            return 1
        if args.command == 'inspect' and not result['ready']:
            return 1
        return 0
    except (ValueError, OSError, SyntaxError, KeyError) as error:
        print(f'Fyzz: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
