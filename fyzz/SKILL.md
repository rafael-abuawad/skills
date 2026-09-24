---
name: fyzz
description: Generate stateful Vyper fuzz suites using Python Hypothesis for ApeWorX, Titanoboa, or Moccasin. Use for Vyper fuzz harnesses, property testing, and invariant campaigns.
---

# Fyzz

Generate a stateful Vyper fuzz suite under `{SUITE_DIR}` (default `test/fuzz/`), with metadata and fuzzer runtime files under `{META_DIR}` (default `fuzz_data/`). Hypothesis is the sole fuzzing engine; the selected framework supplies compilation, deployment, and chain execution.

## Resolve the run

`PROJECT_ROOT` defaults to the current directory; `SKILL_PATH` is this skill's directory. Paths are relative to the project unless explicitly absolute. Preserve existing project configuration and handwritten tests.

- `--framework auto|ape|boa|moccasin`: default `auto`; inspect config and existing tests. Conflicting framework evidence requires clarification, even in automatic mode.
- `--suite-dir`, `--meta-dir`: apply consistently to every helper and generated path.
- Optional contract names limit actions, not deployment dependencies.
- `--automatic` / `--auto`: default; complete the bounded workflow without review prompts. `--guided`: review at the checkpoints below. Resolve once.
- `--no-invariants`: skip property discovery and implementation; retain action reachability, expected-revert checks, and reporting. Label the result as a reachability suite.

Use the project's Python environment. Read [helper commands](references/helpers.md) before invoking scripts; the helper scaffolds infrastructure, while you implement protocol semantics. Missing dependencies, ambiguous compilation, or unsupported ABI types are blockers, not reasons to silently skip tests.

## Workflow

### 1. Inspect, compile, and inventory

Run `python3 {SKILL_PATH}/scripts/fyzz.py inspect {PROJECT_ROOT}` with resolved path/framework flags. Read project configuration, dependency locks, deployment code, existing fixtures, and in-scope `.vy` sources. Read only the selected framework reference: [Ape](references/ape.md), [Titanoboa](references/boa.md), or [Moccasin](references/moccasin.md).

Compile using the existing project toolchain. Export framework/compiler ABIs and run `inventory` with `--artifact` paths as needed. Verify source-to-contract mappings, constructors, callable signatures, and compile settings. Read Vyper source for bounded strings/bytes, array capacities, roles, and semantics absent from the ABI. Do not infer signatures using source regexes.

### 2. Understand and select

Guided: collect additional docs before analysis and save their paths/URLs to `{META_DIR}/additional-context.md`. Read existing analysis (including `x-ray/x-ray.md` if present); no external analysis skill is required.

Write `{META_DIR}/protocol-understanding.md`: deployment order, initialization, actors and permissions, dependencies/mocks, approvals/funding, useful lifecycle actions, and candidate guarantees with evidence. Reuse existing deployment functions; justify mocks.

Refine `{META_DIR}/selection.json` from the normalized inventory. Include useful state transitions and purposeful negative cases; exclude plumbing that cannot be called by modeled actors. Classify selected functions as primary or secondary. Keep rare admin actions available without promising Hypothesis scheduling weights. Guided: review the selection. Record exclusions and unresolved dependencies.

### 3. Scaffold and wire

Run `scaffold`. Read [suite design](references/suite-design.md); implement deployment, bounded strategies, realistic actors, model state, actions, and postconditions in the generated package. The untouched scaffold must fail explicitly: passing placeholder tests are not a completed suite.

Guided: review deployment order, constructor sources, mocks, actors, grants, balances, and approvals. Compile/collect tests and fix setup before continuing. Validate fresh chain and Python state across consecutive state-machine instances, including initialization failure.

### 4. Establish reachability

Run the smoke profile. Inspect successful actions, expected reverts, skipped preconditions, and exercised lifecycle transitions. Improve setup, strategies, actor permissions, and missing actions based on evidence. Read [campaigns](references/campaigns.md) for instrumentation and failure handling.

Automatic: at most three smoke/improvement cycles; document remaining gaps. Guided: after each cycle offer iterate, adjust scope, or proceed. A nonfunctional core flow is an explicit blocker or incomplete outcome, never successful fuzz coverage. Record contract coverage only when the framework actually reports Vyper source coverage.

### 5. Discover and implement properties

Skip only for `--no-invariants`. Read [properties](references/properties.md) and [discovery perspectives](agents/discovery.md). Gather protocol analysis, source, setup, actions, model state, and supplied docs. Apply the five perspectives, delegating bounded independent analyses when available and respecting runtime concurrency limits; inherit the host model. Otherwise analyze sequentially.

Synthesize `{META_DIR}/property-plan.md` and `{META_DIR}/PROPERTIES.md`. Keep stable `GL-NN` / `SP-NN` identifiers, guarantee tags, evidence, dependencies, and implementation associations. Guided: review the property spec, honor edits, and reread before implementation.

Use one integrating writer for model state, properties, and action wiring. Mark properties `[x]` only after implementing and validating both assertions and call sites. Leave unsupported properties pending with specific blockers. Smoke-test the integrated suite; repair specific failures, up to three cycles.

### 6. Campaign, reproduce, report

Guided: review profile and timeout; automatic defaults to standard. Run `run` through the selected framework and track the process with the host execution tool. Preserve logs, database, shrink output, traces, and effective settings under metadata.

For failures, distinguish contract behavior from faulty setup, nondeterminism, bad assumptions, and assertions. Produce deterministic tests under `{SUITE_DIR}` from the shortest reproducible sequence; verify the same property fails, using exact actors, arguments, value, time/block changes, and setup. A seed or database entry alone is not a durable reproduction. Report unconfirmed reproductions explicitly.

Write `{META_DIR}/report.md` with tested scope, framework/compiler versions, commands/settings, action reachability, available Vyper coverage, property status, violations/evidence, reproduction commands, blockers, and next steps. A clean bounded campaign establishes only that no violation was found in that run. Timeouts are incomplete.

Run final smoke/collection checks. After successful suite validation, run `snapshot` to establish or refresh `{META_DIR}/last-run.json`; unresolved harness failures must not become the new baseline. For later property edits use [fyzz-convert](../fyzz-convert/SKILL.md); for source drift use [fyzz-sync](../fyzz-sync/SKILL.md).
