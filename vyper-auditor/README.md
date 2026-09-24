# Vyper Auditor

A parallel security review for Vyper contracts: focused findings in minutes, before
you ship a change.

Built for:

- **Vyper developers** who want a security pass before a commit or deployment
- **Security researchers** who want structured attack coverage before manual review
- **Protocol teams** who need an additional, evidence-driven review of `.vy` code

It is not a substitute for a professional audit. Use it to surface concrete paths
worth fixing or investigating, then test and review the result.

## What it covers

The auditor coordinates 12 independent attack lenses:

1. Math and precision
2. Access control and module initialization
3. Economic security and token behavior
4. Execution traces and transaction interleaving
5. Invariants and conservation laws
6. Periphery, interfaces, encoders, and helpers
7. First-principles assumption breaking
8. Function and branch asymmetry
9. External boundaries and raw-call behavior
10. Numerical gaps across precision, invariants, and boundaries
11. Trust gaps across authority, economics, and asymmetry
12. Flow gaps across execution, periphery, and protocol intent

It also accounts for Vyper-specific semantics: compiler/pragma context, global and
file-scoped nonreentrancy, modules and `exports:`, `extcall`/`staticcall`,
`raw_call`, `default_return_value`, `@raw_return`, blueprint factories,
`raw_create`, transient storage, checked conversions, and `decimal` precision.

## Usage

```bash
# Review all in-scope Vyper contracts in the repository
/vyper-auditor

# Review specific contracts only
/vyper-auditor src/vault.vy src/factory.vy

# Run one pass without cross-scan memory
/vyper-auditor --loop 1

# Run three passes; later passes see earlier findings
/vyper-auditor --loop 3

# Remember findings between single-pass scans
/vyper-auditor --loop 1 --memory

# Also copy the complete report into the project root
/vyper-auditor --file-output
```

Without a supplied count, the skill asks how many passes to run. Bare `--loop`
means three; explicit counts from 1 through 10 are accepted. The twelve specialties
run within the runtime's concurrency limit. Every pass sees the same frozen source.

Every scan saves run records and a complete report under
`.vyper-auditor/runs/YYYYMMDD-HHMMSS/`. Above 20 findings the terminal shows the
counted top three and the full-report path. `--file-output` makes a byte-identical
copy named `{project}-pashov-ai-vyper-audit-report-{stamp}.md` in the project root.

Memory is opt-in for one pass and automatic for multiple passes. It lives in
`.vyper-auditor/memory.tsv`. Findings are NEW or KNOWN across scans; `seen in k/N
runs` describes repetition inside one scan. Previously recorded issues that were
not raised again are explicitly **not re-checked**, not assumed fixed. Invalid
ledgers stop the audit instead of being discarded. Do not run simultaneous scans
that write the same ledger. Consider ignoring `.vyper-auditor/` in version control.

A plain one-pass scan saves run artifacts but does not read or write memory. Audit
agents are read-only in your repository; fixes are suggestions. V4 uses confidence
75 as the fix threshold, with a documented no-fix exception for partial-path
promotions. Proof and compiler evidence remain part of the Vyper report.

The workflow requires Bash, Python 3.10+, awk, `find`, and standard Unix utilities.
Git adds revision metadata; without it, revisions are recorded as `none`. Curl is
used only for the optional version check. Upstream's 15/45/75-minute measurements
were on Solidity with Opus, not Vyper timing guarantees.

## Scope and limitations

By default the skill excludes tests, mocks, interfaces, dependencies, virtual
environments, and build output from finding scope. Deployment `.vy` files remain
in scope. Explicitly named `.vy` files override directory exclusions. Agents can still inspect those files to confirm an interface,
dependency behavior, deployment configuration, or testable attack path.

The best results are usually on roughly 2,500 lines of Vyper or less. Past 5,000
lines, split the review by module or hot contract. The skill is strongest at
concrete code-level paths and weaker at missing specifications, off-chain
assumptions, governance/game theory, and novel cross-protocol composition. Human
review, adversarial tests, formal invariants, bug bounties, and monitoring remain
essential.

## Validation

Run the deterministic fixture suite without launching audit agents:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s vyper-auditor/tests -v
bash -n vyper-auditor/references/assemble.sh
```

The suite covers discovery, Vyper identities, pruning, ledger integrity, repeated
scans, multi-pass assembly, report-size boundaries, and failed coverage. It does
not measure the quality of a live security audit.
