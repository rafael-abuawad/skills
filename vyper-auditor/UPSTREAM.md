# Provenance and Vyper Maintenance

This independent Vyper skill originated as an adaptation of the upstream
[`solidity-auditor`](https://github.com/pashov/skills/tree/main/solidity-auditor)
workflow.

- Historical upstream workflow version: **4**
- Independent Vyper skill version: **5**
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

## Independent version 5

The local `VERSION` now tracks Vyper changes independently. Audit invocations do
not compare it with Solidity-auditor releases or direct users there to upgrade.
The original branded banner is retained; exported reports use
`{project-name}-vyper-audit-report-{stamp}.md` and contain no promotional footer.
The twelve specialties use Vyper instructions directly instead of appended
translation overrides. The workflow, evidence gates, and memory format remain.

## Updating

1. Review the official [Vyper release notes](https://docs.vyperlang.org/en/stable/release-notes.html),
   [security advisories](https://github.com/vyperlang/vyper/security/advisories),
   and language documentation for the supported compiler versions. The stable
   documentation and advisory index were rechecked on 2026-10-02; the covered
   stable release remains 0.4.3.
2. Update `references/vyper-language.md` and affected specialties for changed
   semantics, new features, and affected compiler ranges. Require deployed or
   reproducibly configured version evidence for compiler-specific findings.
3. Review EVM/protocol attack coverage and workflow improvements on their merits.
   The historical Solidity source is optional reference material; adopting changes
   does not require matching its version or porting language-specific assumptions.
4. Increment the local `VERSION` for a Vyper skill release and record material
   changes here, preserving the historical source revision and attribution.
5. Run the fixture suite in README.md, shell syntax checks, skill validation, and
   local reference-link checks. Ensure all active references resolve.
