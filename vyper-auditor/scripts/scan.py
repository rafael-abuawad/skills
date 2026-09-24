#!/usr/bin/env python3
"""Deterministic Vyper scan state, run indexing, and terminal report extraction.

Standard-library only. The shell assembler owns report production; this helper
owns source identities and the one parser shared by assembly and memory writes.
"""
import argparse
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tokenize

HEADER = '#vyper-auditor-memory v1\tkey\tstatus\tscans\tsha\ttitle\tkind'
EXCLUDED = ('node_modules', 'lib', 'artifacts', 'cache', 'out', 'broadcast',
            'coverage', 'typechain*', 'interfaces', 'mocks', 'test', 'tests',
            '.git', '.venv', 'venv', '__pycache__', 'build', 'dist', '.vyper-auditor',
            '.vyper-audit-*')
KEY = re.compile(r'[a-z0-9-]+\|[a-z0-9-]+\|[a-z0-9-]+\Z')


def normalize(value):
    return re.sub('[^a-z0-9]+', '-', value.lower())


def clean(value):
    return re.sub(r'[\t\r\n]+', ' ', str(value))


def atomic(path, text):
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(text, encoding='utf-8')
    os.replace(temporary, path)


def scope_append(directory, **values):
    with (Path(directory) / 'scope.tsv').open('a', encoding='utf-8') as stream:
        for key, value in values.items():
            stream.write(f'{key}\t{clean(value)}\n')


def scope_read(directory):
    path = Path(directory) / 'scope.tsv'
    return dict(line.split('\t', 1) for line in path.read_text().splitlines()) if path.exists() else {}


def read_ledger(path):
    path = Path(path)
    if not path.exists():
        return {}
    lines = path.read_text(encoding='utf-8').splitlines()
    if not lines or lines[0].split('\t')[0] != HEADER.split('\t')[0]:
        raise ValueError(f'{path}: invalid memory header')
    rows = {}
    for number, line in enumerate(lines[1:], 2):
        row = line.split('\t')
        if (len(row) != 6 or not KEY.fullmatch(row[0]) or row[1] not in ('NEW', 'KNOWN')
                or not row[2].isdigit() or int(row[2]) < 1
                or row[5] not in ('FINDING', 'LEAD') or row[0] in rows):
            raise ValueError(f'{path}:{number}: invalid or duplicate six-column memory record')
        rows[row[0]] = row
    return rows


def ledger_text(rows):
    return HEADER + '\n' + ''.join('\t'.join(row) + '\n' for row in rows.values())


def discover(root, files):
    if files:
        candidates = [Path(os.path.abspath(root / item)) for item in files]
    else:
        command = ['find', '.', '-type', 'f', '-name', '*.vy']
        for name in EXCLUDED:
            command += ['-not', '-path', f'*/{name}/*']
        for name in ('*Test*.vy', '*Mock*.vy', '*_test.vy'):
            command += ['-not', '-name', name]
        command += ['-print0']
        found = subprocess.run(command, cwd=root, check=True, capture_output=True).stdout
        candidates = [root / os.fsdecode(item) for item in found.split(b'\0') if item]
    result = []
    for path in candidates:
        if not path.is_file() or path.suffix != '.vy':
            raise ValueError(f'{path}: expected an existing .vy file')
        relative = os.path.relpath(path, root)
        if any(ch in relative for ch in '\t\r\n`|'):
            raise ValueError(f'{relative!r}: unsupported source path delimiter')
        if relative not in result:
            result.append(relative)
    return result


def source_identity(source):
    """Lex source, never compile it. Unresolved exports/token errors forbid pruning.

    Tokenization excludes comments and strings and joins multiline annotations.
    Keeping extra function names is safe; deleting uncertain names is not.
    """
    functions = {'__module__'}
    uncertain = False
    tokens = []
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return functions, True
    for index, token in enumerate(tokens):
        if token.type == tokenize.NAME and token.string == 'def' and index + 1 < len(tokens):
            functions.add(tokens[index + 1].string)
        if token.start[1] == 0 and token.type == tokenize.NAME:
            if token.string == 'exports':
                uncertain = True
            following = tokens[index + 1:]
            logical = []
            for item in following:
                if item.type == tokenize.NEWLINE:
                    break
                logical.append(item.string)
            if logical and logical[0] == ':' and 'public' in logical:
                functions.add(token.string)
    return functions, uncertain


def build_index(sources):
    index, names, module_keys = {}, {}, {}
    for path, source in sources.items():
        module = normalize(path)
        if module in module_keys and module_keys[module] != path:
            raise ValueError(f'identity collision: {module_keys[module]} and {path}')
        module_keys[module] = path
        functions, uncertain = source_identity(source)
        identifiers = {}
        for function in sorted(functions):
            key = normalize(function)
            if key in identifiers and identifiers[key] != function:
                raise ValueError(f'identity collision in {path}: {identifiers[key]} and {function}')
            identifiers[key] = function
            names[f'{module}|{key}'] = f'{path}.{function}'
        index[module] = {'path': path, 'functions': identifiers, 'uncertain': uncertain}
    return index, names


def prepare(args):
    root = Path(args.root).resolve()
    files = discover(root, args.files)
    if not files:
        raise ValueError('No in-scope Vyper source files; no agents or report.')
    sources = {path: (root / path).read_text(encoding='utf-8') for path in files}
    index, names = build_index(sources)
    memory = args.memory or args.passes > 1
    ledger = root / '.vyper-auditor/memory.tsv'
    before = read_ledger(ledger) if memory else {}
    if memory and ledger.with_name('memory.tsv.tmp').exists():
        print(f'warning: {ledger}.tmp left by an unfinished scan — overwriting', file=sys.stderr)
    pruned = []
    if memory and not args.files:
        for key, row in list(before.items()):
            module, function, _ = key.split('|')
            entry = index.get(module)
            if entry is None or (function not in entry['functions'] and not entry['uncertain']):
                pruned.append(row)
                del before[key]
    if pruned:
        print(f'Pruned {len(pruned)} records (file or function no longer in scope):')
        for row in pruned:
            print(f'{row[5]}\t{row[0]}\t{row[4]}')
    if not re.fullmatch(r'\d{8}-\d{6}', args.stamp):
        raise ValueError('stamp must be YYYYMMDD-HHMMSS')
    directory = root / '.vyper-auditor/runs' / args.stamp
    if directory.exists():
        raise ValueError(f'{directory}: scan stamp already exists; choose a new stamp')
    bundle = Path(args.bundle).resolve()
    bundle.mkdir(parents=True, exist_ok=True)
    directory.mkdir(parents=True)
    try:
        sha = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=root,
                             capture_output=True, text=True).stdout.strip() or 'none'
    except FileNotFoundError:
        sha = 'none'
    state = {'root': str(root), 'directory': str(directory), 'memory': memory,
             'passes': args.passes, 'sha': sha, 'completed': [], 'names': names}
    (bundle / 'state.json').write_text(json.dumps(state), encoding='utf-8')
    (bundle / 'source.md').write_text(''.join(
        f'### {path}\n\n```vyper\n{source.rstrip()}\n```\n\n' for path, source in sources.items()), encoding='utf-8')
    (bundle / 'source-index.json').write_text(json.dumps(index), encoding='utf-8')
    names_text = ''.join(f'{key}\t{value}\n' for key, value in names.items())
    (bundle / 'source-names.tsv').write_text(names_text, encoding='utf-8')
    # A JSON array preserves spaces in paths; it is still a single TSV value.
    scope_append(directory, name=root.name, mode='filename' if args.files else 'default',
                 files=json.dumps(files), compiler_context='not verified', passes_planned=args.passes)
    if memory:
        (bundle / 'memory-before.tsv').write_text(ledger_text(before), encoding='utf-8')
        (directory / 'memory-before.tsv').write_text(ledger_text(before), encoding='utf-8')
        (directory / 'source-names.tsv').write_text(names_text, encoding='utf-8')
        scope_append(directory, mem_before=len(before), mem_after=len(before), mem_sha=sha)
    print(json.dumps({'run_directory': str(directory), 'files': files, 'memory': memory}))


def load_state(bundle):
    return json.loads((Path(bundle) / 'state.json').read_text(encoding='utf-8'))


def known(args):
    bundle = Path(args.bundle)
    state = load_state(bundle)
    target = bundle / 'known-findings.md'
    target.unlink(missing_ok=True)
    if not state['memory']:
        return
    path = (Path(state['root']) / '.vyper-auditor/memory.tsv' if state['completed']
            else bundle / 'memory-before.tsv')
    rows = read_ledger(path)
    if not rows:
        return
    groups = {}
    for key, row in rows.items():
        prefix, bug = key.rsplit('|', 1)
        display = state['names'].get(prefix, prefix.replace('|', '.'))
        groups.setdefault(display, []).append(
            f'- `{bug}` — {row[5]}, seen in {row[2]} scan(s) — {row[4]}')
    text = '''# Known findings — ground already walked

Earlier scans and completed passes recorded these findings. Spend reading effort
on new functions, flows, and mechanisms. Report every bug you find in full,
including listed bugs: the same path, proof, and fix. Silence means not re-checked,
not fixed. These records are neither false positives nor off limits.

Reuse the exact bug-class label for the same class of bug in the same file and
function. Invent a label only for a different defect. The label is a memory key,
not prose to improve. Scan counts and pass counts are different quantities.

'''
    text += '\n\n'.join(f'## {display}\n\n' + '\n'.join(lines) for display, lines in groups.items()) + '\n'
    target.write_text(text, encoding='utf-8')


def parse_run(path):
    """Return assembler index records and explicit structural diagnostics."""
    path = Path(path)
    lines = path.read_text(encoding='utf-8').splitlines()
    expected = int(re.fullmatch(r'run-(\d+)\.md', path.name)[1])
    errors, records = [], []
    header = re.fullmatch(r'<!--RUN pass=(\d+) agents=(\d+)/12-->', lines[0] if lines else '')
    if not header or int(header[1]) != expected or not 1 <= int(header[2]) <= 12:
        errors.append(f'{path.name}: missing or invalid RUN header')
    start = None
    for line_number, line in enumerate(lines, 1):
        if line.startswith('<!--F '):
            if start is not None:
                errors.append(f'{path.name}:{start}: unclosed finding')
            start = line_number
        elif line == '<!--/F-->':
            if start is None:
                errors.append(f'{path.name}:{line_number}: unmatched closing marker')
                continue
            block = lines[start - 1:line_number]
            try:
                marker = re.fullmatch(r'<!--F key=(\S+)(?: conf=(\d+))? kind=(FINDING|LEAD) agents=([0-9,]+)-->', block[0])
                if not marker or not KEY.fullmatch(marker[1]):
                    raise ValueError('invalid F marker')
                key, confidence, kind, agents = marker.groups()
                if (kind == 'FINDING' and (confidence is None or not 1 <= int(confidence) <= 100)
                        or kind == 'LEAD' and confidence is not None):
                    raise ValueError('invalid confidence')
                if any(not 1 <= int(agent) <= 12 for agent in agents.split(',')):
                    raise ValueError('invalid agent attribution')
                if len(block) < 5 or block[1] != '' or block[3] != '':
                    raise ValueError('invalid block spacing')
                if kind == 'FINDING':
                    title_match = re.fullmatch(r'\[(\d+)\] \*\*(.+)\*\*', block[2])
                    location_match = re.fullmatch(r'`([^`]+)` · Confidence: (\d+)', block[4])
                    if not title_match or not location_match or title_match[1] != confidence or location_match[2] != confidence:
                        raise ValueError('title/location disagrees with marker')
                    title, location = title_match[2], location_match[1]
                    if len(block) < 8 or block[5] != '':
                        raise ValueError('missing finding body')
                    body = '\n'.join(block[6:-1])
                    if '**Description**' not in body or '**Proof**' not in body:
                        raise ValueError('finding needs Description and Proof')
                    leadbody = '-'
                else:
                    lead = re.fullmatch(r'- \*\*(.+)\*\* — `([^`]+)` — (.+)', block[2])
                    if not lead or len(block) != 5:
                        raise ValueError('invalid lead block')
                    title, location, leadbody = lead.groups()
                file_name, function = location.rsplit('.', 1)
                if '|'.join((normalize(file_name), normalize(function))) != key.rsplit('|', 1)[0]:
                    raise ValueError('location disagrees with key')
                if any('\t' in value for value in (title, location, leadbody)):
                    raise ValueError('tab in title/location/lead')
                records.append([key, confidence or '-', kind, agents, str(path), str(expected),
                                str(start), str(line_number), str(start + 6), str(line_number - 1),
                                title, location, leadbody])
            except (ValueError, IndexError) as error:
                errors.append(f'{path.name}:{start}: {error}')
            start = None
        elif line.startswith('<!--F') or line.startswith('<!--/F'):
            errors.append(f'{path.name}:{line_number}: malformed finding marker')
    if start is not None:
        errors.append(f'{path.name}:{start}: unclosed finding')
    return records, errors


def index_runs(args):
    directory = Path(args.dir)
    errors = []
    for path in sorted(directory.glob('run-*.md'), key=lambda p: int(p.stem[4:]) if p.stem[4:].isdigit() else -1):
        if not re.fullmatch(r'run-[1-9][0-9]*\.md', path.name):
            errors.append(f'{path.name}: invalid run filename')
            continue
        records, problems = parse_run(path)
        header = re.match(r'<!--RUN pass=(\d+) agents=(\d+/12)-->', path.read_text(encoding='utf-8'))
        actual = scope_read(directory).get(f'pass_{int(path.stem[4:])}_agents')
        if header and header[2] != actual:
            problems.append(f'{path.name}: agent count missing or differs from scope')
        errors.extend(problems)
        for record in records:
            print('\t'.join(record))
    Path(args.diagnostics).write_text('; '.join(errors), encoding='utf-8')


def merge(args):
    bundle = Path(args.bundle)
    state = load_state(bundle)
    if not state['memory']:
        raise ValueError('memory is off; merge is forbidden')
    directory = Path(state['directory'])
    if args.pass_number > state['passes']:
        raise ValueError('pass exceeds planned count')
    if args.pass_number not in state['completed'] and args.pass_number != len(state['completed']) + 1:
        raise ValueError('passes must be merged in order')
    before = read_ledger(bundle / 'memory-before.tsv')
    live = Path(state['root']) / '.vyper-auditor/memory.tsv'
    previous = read_ledger(live) if state['completed'] else before
    passes = sorted(set(state['completed'] + [args.pass_number]))
    accumulated = {}
    current = []
    for number in passes:
        records, errors = parse_run(directory / f'run-{number}.md')
        if errors:
            raise ValueError('ledger unchanged: ' + '; '.join(errors))
        for record in records:
            accumulated[record[0]] = record
        if number == args.pass_number:
            current = records
    merged = {key: row[:] for key, row in before.items()}
    for key, record in accumulated.items():
        old = before.get(key)
        merged[key] = [key, 'KNOWN' if old else 'NEW', str(int(old[2]) + 1 if old else 1),
                       state['sha'], clean(record[10])[:80], record[2]]
    atomic(live, ledger_text(merged))
    scope_append(directory, mem_after=len(merged), mem_sha=state['sha'])
    state['completed'] = passes
    atomic(bundle / 'state.json', json.dumps(state))
    if state['passes'] > 1:
        counts = {kind: len({r[0] for r in current if r[2] == kind}) for kind in ('FINDING', 'LEAD')}
        new = {kind: len({r[0] for r in current if r[2] == kind and r[0] not in previous}) for kind in counts}
        parts = []
        for kind, label in [('FINDING', 'findings'), ('LEAD', 'leads')]:
            parts.append(f'{counts[kind]} {label}' + (f' ({new[kind]} new)' if before else ''))
        parts.append(f'ledger {len(merged)} records')
        agents = scope_read(directory).get(f'pass_{args.pass_number}_agents', 'unknown/12')
        if agents != '12/12':
            parts.append(f'{agents} agents')
        if not any(new.values()):
            parts.append('no new ground')
        print(f"Pass {args.pass_number}/{state['passes']} — " + ' · '.join(parts))


def terminal(args):
    directory = Path(args.dir)
    report = directory / 'full-report.md'
    text = report.read_text(encoding='utf-8')
    target = report
    if args.file_output:
        name = scope_read(directory)['name']
        # name comes from the root basename, never from a finding or a shell command.
        target = directory.parent.parent.parent / f'{name}-pashov-ai-vyper-audit-report-{directory.name}.md'
        target.write_bytes(report.read_bytes())
    findings = re.findall(r'^\[(\d+)\] \*\*\d+\. (.+)\*\*\n\n(`[^`]+` · Confidence: \d+[^\n]*)', text, re.M)
    count = len(re.findall(r'^\[\d+\] \*\*', text, re.M))
    if count <= 20 or len(findings) != count:
        if len(findings) != count:
            print('warning: malformed finding counts; printing the full report', file=sys.stderr)
        print(text, end='')
        if args.file_output:
            print(f'\nReport copy: {target}')
        return
    scope = text.split('## Scope\n', 1)[1].split('\n---', 1)[0]
    print(text.splitlines()[0] + '\n\n---\n\n## Scope\n' + scope)
    print(f'---\n\nFindings List — top 3 of {count}\n')
    seen_column = '**Passes**' in scope
    print('| # | Confidence | Title | Location |' + (' Seen |' if seen_column else ''))
    print('|---|---|---|---|' + ('---|' if seen_column else ''))
    for number, (confidence, title, meta) in enumerate(findings[:3], 1):
        location = re.search(r'`[^`]+`', meta)[0]
        seen = re.search(r'seen in (\d+/\d+) runs', meta)
        print(f'| {number} | [{confidence}] | {title} | {location} |' +
              (f' {seen[1] if seen else "—"} |' if seen_column else ''))
    print(f'\n**→ Full findings list, every description and every fix:** {target}\n\n---\n')
    print(next(line for line in text.splitlines() if line.startswith('> ⚠️')))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prepare_parser = commands.add_parser('prepare')
    prepare_parser.add_argument('--root', default='.')
    prepare_parser.add_argument('--bundle', required=True)
    prepare_parser.add_argument('--stamp', required=True)
    prepare_parser.add_argument('--passes', type=int, choices=range(1, 11), required=True)
    prepare_parser.add_argument('--memory', action='store_true')
    prepare_parser.add_argument('files', nargs='*')
    for command in ('known', 'merge'):
        p = commands.add_parser(command)
        p.add_argument('--bundle', required=True)
        if command == 'merge':
            p.add_argument('--pass', dest='pass_number', type=int, choices=range(1, 11), required=True)
    p = commands.add_parser('index-runs')
    p.add_argument('--dir', required=True)
    p.add_argument('--diagnostics', required=True)
    p = commands.add_parser('terminal')
    p.add_argument('--dir', required=True)
    p.add_argument('--file-output', action='store_true')
    args = parser.parse_args()
    try:
        {'prepare': prepare, 'known': known, 'merge': merge, 'index-runs': index_runs, 'terminal': terminal}[args.command](args)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(f'scan.py: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
