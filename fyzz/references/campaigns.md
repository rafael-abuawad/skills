# Campaigns, reachability, and reproduction

| Profile | max_examples | stateful_step_count |
| --- | ---: | ---: |
| smoke | 10 | 20 |
| standard | 100 | 50 |
| extended | 1,000 | 100 |

Set `deadline=None`; allow explicit setting overrides and save effective values. These are generation budgets, not guarantees about exact transaction count or elapsed time: shrinking and database replay add execution. Store the Hypothesis example database under metadata. Keep version, selected profile, runner argv, seed when supplied, and final outcome beside logs.

Use a tracked foreground process through the host's asynchronous command interface. Do not shell-background and lose its handle. With an optional wall timeout, stop the process tree, retain output, and mark the campaign incomplete even if no property failure appeared before termination. Do not silently suppress health checks; correct their cause or document a narrowly justified suppression.

## Reachability evidence

Instrument each action's attempts, successes, and deliberate expected reverts. Persist per-example action records and aggregate observations across the run, including shrink executions. Label this distinction so repeated shrink attempts are not presented as unique fuzz coverage. Track state transitions such as deposit→withdraw, request→finalize, borrow→repay, and unauthorized→rejected.

For selected but unexecuted flows, inspect preconditions, actor funding, setup, and strategy filtering. Keep exclusions and external-state requirements explicit. Do not infer contract branch coverage from action counts. If framework contract coverage is unavailable, report it as unavailable; Python line coverage belongs to the harness only. Contract coverage requires verified `.vy` attribution, a documented denominator, and exclusions for mocks/dependencies.

## Replay records

Record action name/full signature, actor index, concrete arguments, value, time/block adjustments, outcome, and relevant pre/post state. Serialize bytes, integers, tuples, and addresses losslessly. Keep records per machine example; failed examples encountered while shrinking are not necessarily the final minimum. Retain Hypothesis's final falsifying output alongside records and select the shortest sequence that independently reproduces.

Create a deterministic pytest reproduction under `{SUITE_DIR}` using the same setup and action implementations. Replay all pre-failure operations, then check the named property or execute the final action. The reproduction must fail for the same guarantee when run against the unfixed contract. A blanket exception assertion that also accepts deployment errors proves nothing. If a passing proof test is desired, catch only the identified assertion and verify its stable property ID.

Database reuse and seeds help investigation but are not portable replay formats. Document Python/Hypothesis/framework/compiler versions and all environment prerequisites. If shrinking was interrupted or nondeterminism prevents reproduction, report that limitation instead of asserting confirmation.

## Report and completion

Report tested scope, exclusions, versions/settings, per-action reachability, property counts/status, exact failure/reproduction commands, coverage provenance, blockers, and remaining TODOs. Separate clean completion, confirmed guarantee violations, exploratory leads, infrastructure failure, and timeout. A confirmed contract defect can coexist with a valid harness; a faulty harness cannot be a successful validation baseline.

Source: [Hypothesis stateful execution](https://hypothesis.readthedocs.io/en/latest/stateful.html).
