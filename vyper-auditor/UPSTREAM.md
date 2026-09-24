# Coverage Baseline

This skill is a Vyper adaptation of the upstream
[`solidity-auditor`](https://github.com/pashov/skills/tree/main/solidity-auditor)
workflow.

- Upstream workflow version: **4**
- Upstream source revision reviewed: `f6c7f0de9cce16f6aa9c57aaac104f0dee90582e`
- Vyper stable release baseline researched: **0.4.3**

The Vyper version is intentionally not a mechanical Solidity translation. It adds
compiler-version gating, Vyper module/`exports:` lifecycle checks, version-aware
nonreentrancy, `extcall`/`staticcall`/`raw_call` return semantics,
`default_return_value` and `skip_contract_check`, `@raw_return`, blueprint and raw
factories, transient storage, checked conversions, and `decimal` precision.

## Version 4 port

Reviewed against the pinned upstream release on 2026-09-24. The installed
Solidity-auditor files matched that revision. All twelve specialist files and the
senior SOP were unchanged from upstream v3; their existing Vyper adaptations stay.
The shared rules gained the upstream report-language requirement.

Ported loop mode, memory, explicit scope overrides, numeric upgrade checks,
read-only agent prompts, threshold 75 and lead-promotion exception, deterministic
report assembly, failure visibility, and the counted top-three terminal view.
The shell assembler derives from upstream `references/assemble.sh`.

Intentional adaptations:

- Vyper source paths identify contracts/modules; function spelling and compiler
  evidence remain visible. The index includes getters and dunder functions.
- A standard-library Python helper replaces inline memory commands and the run
  parser with one tested implementation shared by memory and shell assembly.
  Pruning compares file/function pairs and retains uncertain exported functions.
- A JSON array inside the `files` TSV value preserves spaces in source paths.
- Reports retain Vyper Proof blocks, Compiler context, and agent attribution.
- Agent scheduling respects runtime concurrency limits without dropping specialties.
- Contradictory upstream “nothing written” wording is resolved: run artifacts are
  always saved; ledger access remains conditional. Single-pass agent loss is visible.
- Missing or malformed inputs and memory-write errors are reported rather than
  claiming complete coverage or successful persistence.

Rechecked the [Vyper release notes](https://docs.vyperlang.org/en/stable/release-notes.html)
and [advisory index](https://github.com/vyperlang/vyper/security/advisories).
The covered stable baseline remains 0.4.3. Preserve the advisory index's ID mapping:
the release notes contain mismatched links for the 0.4.2 concat/slice fixes.

## Updating

When upstream releases a new `solidity-auditor` version:

1. Diff the full pinned skill, including helper scripts, prompts, report language,
   judging, report assembly, senior SOP, and all twelve specialist files.
2. Port every general EVM/protocol pattern, preserving the 12-agent topology and
   deduplication/fix-preservation gates.
3. Check Vyper release notes and security advisories. Update
   `references/vyper-language.md` with any new language feature, changed semantic,
   or affected compiler range; do not turn a compiler advisory into a finding
   without deployed-version evidence.
4. Update `VERSION` only when the Vyper skill reaches the current upstream
   coverage baseline, and update this file's revision and release baseline.
5. Run the fixture suite in README.md, shell syntax checks, skill validation, and
   local reference-link checks. Ensure all active references resolve.
