# Coverage Baseline

This skill is a Vyper adaptation of the upstream
[`solidity-auditor`](https://github.com/pashov/skills/tree/main/solidity-auditor)
workflow.

- Upstream workflow version: **3**
- Upstream source revision reviewed: `c577eb7799c349de0acb187ba00ca98e14e436fd`
- Vyper stable release baseline researched: **0.4.3**

The Vyper version is intentionally not a mechanical Solidity translation. It adds
compiler-version gating, Vyper module/`exports:` lifecycle checks, version-aware
nonreentrancy, `extcall`/`staticcall`/`raw_call` return semantics,
`default_return_value` and `skip_contract_check`, `@raw_return`, blueprint and raw
factories, transient storage, checked conversions, and `decimal` precision.

## Updating

When upstream releases a new `solidity-auditor` version:

1. Diff its `SKILL.md`, `judging.md`, `report-formatting.md`, senior SOP, and all
   twelve specialist files against this skill.
2. Port every general EVM/protocol pattern, preserving the 12-agent topology and
   deduplication/fix-preservation gates.
3. Check Vyper release notes and security advisories. Update
   `references/vyper-language.md` with any new language feature, changed semantic,
   or affected compiler range; do not turn a compiler advisory into a finding
   without deployed-version evidence.
4. Update `VERSION` only when the Vyper skill reaches the current upstream
   coverage baseline, and update this file's revision and release baseline.
5. Run the structural checks documented in the task/CI and ensure no active SKILL
   path refers to retired legacy vector files.
