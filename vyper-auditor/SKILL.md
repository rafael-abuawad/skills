---
name: vyper-auditor
description: Security audit of Vyper contracts, modules, or specified .vy files. Use for audits, security reviews, loop mode, or repeated audit passes. Supports findings memory between scans and one combined report.
---

# Smart Contract Security Audit (Vyper)

Coordinate twelve attack specialties, validate their evidence, and produce one
report. Preserve compiler-version evidence and Vyper semantics throughout.

## Modes and artifacts

- **Default:** discover `.vy` files with Bash `find -type f`, through the prepare
  helper below. Exclude dependencies/build output (`node_modules/`, `lib/`,
  `artifacts/`, `cache/`, `out/`, `broadcast/`, `coverage/`, `typechain*/`,
  `.venv/`, `venv/`, `__pycache__/`, `build/`, `dist/`), `.git/`, audit artifacts,
  interfaces, mocks, `test/`, `tests/`, and `*Test*.vy`, `*Mock*.vy`, `*_test.vy`.
  `script/`, `scripts/`, and `deploy/` remain in scope. Python deployment scripts
  are context for a Vyper path; default discovery does not become a Python audit.
- **Named files:** scan only explicitly named `.vy` files, including files under
  excluded directories. Reject missing files; never silently broaden scope.
  Agents may inspect imports, interfaces, tests, and deployment configuration as
  context, without expanding finding scope.
- **`--loop [N]`:** N passes, 1–10; a bare flag means 3. Explicit natural language
  such as “audit this four times” also settles the count. “Loop mode” without a
  count requires the picker below.
- **`--memory`:** remember findings and leads between scans. Off unless requested
  or the pass count exceeds 1.
- **`--file-output`:** copy the assembled report to
  `{project-name}-pashov-ai-vyper-audit-report-{stamp}.md` in the audited root.
  It never regenerates the report.

A **scan** is one invocation; a **run** is one pass of twelve specialties. Ledger
`scans` counts invocations. `seen in k/N runs` counts successful run files in this
scan. Never substitute one count for the other.

Every scan with source creates `.vyper-auditor/runs/{stamp}/scope.tsv`, completed
`run-K.md` files, and `full-report.md`. A plain one-pass scan reads/writes no ledger,
writes no `mem_` scope keys, and prints no memory/pass labels or pass summary.
It still saves run artifacts. `--memory` with one pass enables memory alone.
Temporary `.vyper-audit-*` bundles are removed at the end. Nothing else is written
outside `.vyper-auditor/` unless `--file-output` is requested. Do not edit `.gitignore`;
mention the directory in usage documentation so the runner can choose to ignore it.

## Turn 1 — Discover and settle the scan

Print the banner below. Resolve this skill's own directory; `{resolved_path}` is
its `references/` directory, not another auditor's similarly named references.
`{helper}` is the sibling `scripts/scan.py`. It requires Bash, Python 3.10+, awk,
and standard Unix utilities; verify availability before work. Missing runtime:
stop with the missing command, without substituting a model-written report.

In parallel, read local `VERSION`, discover the runtime's agent tool, and fetch
`https://raw.githubusercontent.com/pashov/skills/main/solidity-auditor/VERSION`
with `curl -sf --max-time 10`. Warn only if both values parse as numbers and local
is lower: “⚠️ The Vyper auditor is behind the Solidity-auditor coverage baseline.
Please upgrade: https://github.com/pashov/skills”. Fetch failure is silent.

### Turn 1b — Model and pass picker

Ask only unanswered questions. On Claude Code with model-selectable Agent calls,
ask which family (`opus`, `sonnet`, `haiku`) to use; recommend the orchestrator's
family. On other runtimes leave the model unset and inherit the runtime default.
Do not ask a Claude-model question on a different runtime.

If no explicit pass count arrived, ask using the runtime's question tool, together
with the model question when applicable:

“How many passes should this audit run? Each pass covers all twelve specialties.
Later passes see earlier findings and hunt new ground. You get one combined report.”

Offer **3 passes (Recommended)**, **1 pass**, **5 passes**, allowing a custom count.
Without a question tool print those choices with their literal pass counts and
wait for an answer. Never start agents with an assumed count. Parse the first
integer (or a clearly spelled-out number); outside 1–10, ask once more, then use
1 on a second unusable answer. An explicitly dismissed optional picker means 1;
an unanswered conversational question remains pending. Previously supplied invalid
counts use the same validation. Bare `--loop` has already selected 3; ask nothing.

Upstream measured about 15/45/75 minutes on a 2,228-line Solidity project using
Opus. These are not Vyper benchmarks or promises. Cost and runtime grow with
passes, source size, model, and concurrency limits.

### Turn 1c — Freeze source and open state

Compute `{stamp}` once with `date +%Y%m%d-%H%M%S`; use it for every artifact.
Create `{bundle_dir}` with `mktemp -d ./.vyper-audit-XXXXXX`. Run:

```bash
python3 "{helper}" prepare --root . --bundle "{bundle_dir}" --stamp "{stamp}" --passes {passes}
```

Add `--memory` only when explicitly requested (multiple passes enable it anyway).
For named mode append `--` and each individually shell-quoted path. Placeholders
are values, not shell code; never interpolate untrusted source or finding text
into commands. Use structured file writes or safely quoted arguments.

The helper executes default `find`, validates explicit scope, freezes source and
SHA, rejects normalized identity collisions, and returns the run directory.
No files: remove this scan's bundle and stop without agents. Invalid ledger:
print the path/error, remove the bundle, and stop without report or ledger writes.
An existing stamp is an error; obtain a fresh stamp rather than overwrite a scan.
Read [scan-state.md](references/scan-state.md) when memory is enabled or an identity
is unclear. Its immutable snapshot and pruning rules are implemented by the helper.

## Turn 2 — Prepare each pass

Read in parallel, once per scan:

- [report-formatting.md](references/report-formatting.md): run blocks and report shape.
- [judging.md](references/judging.md): gates, threshold, and promotion exceptions.
- [agent-prompts.md](references/agent-prompts.md): prompts for the two agent groups.
- [report-language.md](references/report-language.md): title/description wording.

Source is already frozen in `{bundle_dir}/source.md`; never rebuild it between
passes. Review compiler configuration and append its evidence summary as the
`compiler_context` key in the run directory's `scope.tsv`; use “not verified”
where necessary. Scope is append-only `key<TAB>value`, last value wins. Strip
embedded tabs/newlines from values. `files` is a JSON array written by the helper,
so spaces in paths remain intact. Never write `mem_` keys on a plain scan.

Every pass, run `python3 "{helper}" known --bundle "{bundle_dir}"`. This reads no
ledger with memory off. With memory on it uses the pruned pre-scan snapshot for
pass 1 and the merged live ledger thereafter. It removes stale known-findings
output and creates no file when there are no records.

Build all twelve bundles with shell `cat`, from files, in this order:
`source.md` + `senior-auditor-sop.md` + `vyper-language.md` + specialty +
`hacking-agents/shared-rules.md` + `report-language.md` + `known-findings.md`
(only when the last file exists). References are under `{resolved_path}`.

| Agent | Specialty under `hacking-agents/` |
| --- | --- |
| 1 | `math-precision-agent.md` |
| 2 | `access-control-agent.md` |
| 3 | `economic-security-agent.md` |
| 4 | `execution-trace-agent.md` |
| 5 | `invariant-agent.md` |
| 6 | `periphery-agent.md` |
| 7 | `first-principles-agent.md` |
| 8 | `asymmetry-agent.md` |
| 9 | `boundary-agent.md` |
| 10 | `numerical-gap-agent.md` |
| 11 | `trust-gap-agent.md` |
| 12 | `flow-gap-agent.md` |

Print line counts for source and bundles. Keep source out of agent-call prompts.

## Turn 3 — Run the twelve specialties

Use the single-specialty template for agents 1–9 and gap-hunter template for
10–12. Include each template's Vyper identity rules in every call. Include the
known-findings paragraph only when that file was appended. The read-only rule is
unconditional: agents never write tests, PoCs, notes, or any file in the audited
repository, including temporary files they intend to delete.

Launch background agents up to the runtime's available concurrency; queue the
remaining specialties and launch them as slots become available. All twelve
specialties are attempted once per pass. Pass a model only if the picker set one.
Use completion notifications or the runtime's native wait primitive; do not poll
or sleep. Read [dedup-and-assembly.md](references/dedup-and-assembly.md) while the
first pass runs. It governs Turns 4 and 5.

A failed agent is not retried. Record its specialty and loss in the run header's
following prose and `pass_K_agents` scope key. Wait for every running agent and
attempt every queued specialty before deduplication. Never overwrite bundles
while any agent still reads them.

If a bundle build fails or all agents fail, append `pass_K_failed<TAB>1`, write no
run file, stop the loop, and perform Turn 5. First-pass failure makes no ledger
write; later failure retains earlier completed passes. The report must expose
lost coverage even in a one-pass scan.

## Turn 4 — Deduplicate, validate, record

Follow [dedup-and-assembly.md](references/dedup-and-assembly.md), Turn 4, once per
completed pass. Write full evidence while the pass's context is available. Merge
memory only when enabled. Then return to Turn 2 until the selected count is reached.

## Turn 5 — Assemble, print, clean

Follow [dedup-and-assembly.md](references/dedup-and-assembly.md), Turn 5, once.
The shell assembler produces the report; the helper extracts terminal output and
copies it when requested. Never regenerate, summarize, or silently truncate the
assembled findings. Remove only this scan's temporary bundle, including on errors;
retain run artifacts and the last complete ledger. Do not sweep other scan folders.

## Banner

Before doing anything else, print this exactly:

```
██████╗  █████╗ ███████╗██╗  ██╗ ██████╗ ██╗   ██╗     ███████╗██╗  ██╗██╗██╗     ██╗     ███████╗
██╔══██╗██╔══██╗██╔════╝██║  ██║██╔═══██╗██║   ██║     ██╔════╝██║ ██╔╝██║██║     ██║     ██╔════╝
██████╔╝███████║███████╗███████║██║   ██║██║   ██║     ███████╗█████╔╝ ██║██║     ██║     ███████╗
██╔═══╝ ██╔══██║╚════██║██╔══██║██║   ██║╚██╗ ██╔╝     ╚════██║██╔═██╗ ██║██║     ██║     ╚════██║
██║     ██║  ██║███████║██║  ██║╚██████╔╝ ╚████╔╝      ███████║██║  ██╗██║███████╗███████╗███████║
╚═╝     ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝   ╚═══╝       ╚══════╝╚═╝  ╚═╝╚═╝╚══════╝╚══════╝╚══════╝
```
