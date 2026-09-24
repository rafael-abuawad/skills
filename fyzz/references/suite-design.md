# Stateful suite design

Use Hypothesis `RuleBasedStateMachine` with meaningful `@rule` actions and `@invariant` checks, invoked by a pytest test through `run_state_machine_as_test`. Read the generated template interfaces before refining them. Keep setup, strategies, model, actions, and properties separate; avoid a second independent harness for replay.

## Isolation and lifecycle

Each machine starts with a framework snapshot/anchor and fresh Python state. Own the context with an `ExitStack` or equivalent. If deployment or initialization raises inside the constructor, close the context in that exception path before re-raising; Hypothesis cannot call teardown on an object whose construction never completed. Normal teardown must close it even if trace persistence fails. Setup should be deterministic for fixed arguments.

Pytest fixtures live outside individual Hypothesis examples. Pass immutable fixture inputs or a deployment factory; invoke the factory after entering isolation. Test two consecutive machine instances plus construction/rule failures to demonstrate chain balances, storage, timestamps, and Python ghost state do not leak. Keep framework handles out of module-level mutable caches.

## Actions and strategies

Use compiler ABI types plus Vyper source bounds. Explicitly constrain integer widths/signedness, fixed bytes lengths, address actors, bounded byte/string lengths, fixed/dynamic arrays, and nested tuple components. Preserve ABI overload/full-signature identity. Decimal/fixed-point or unsupported nested types require a verified encoding strategy or a recorded blocker; guessing can cause invalid tests.

Generate valid operations from current state: actor balances, allowances, capacities, pending requests, and lifecycle preconditions. Draw dynamic values using state-aware strategies or `st.data()`. Avoid excessive `assume()` filtering and `random`/wall-clock values. Use preconditions to avoid impossible actions, but instrument precondition starvation and retain rules that progress the lifecycle.

Keep negative actions explicit: unauthorized callers, zero/boundary values, expired requests, and over-capacity operations. An expected rejection must be tied to the chosen case and, where available, exact reason. Count it separately. Broad `except Exception`, catching assertion failures, or treating every revert as expected hides defects. Snapshot relevant state before a rejected transaction and check required non-mutation afterward.

Primary and secondary are semantic metadata, not promised probabilities. A secondary dispatcher can reduce the number of independently available rules, but Hypothesis chooses inputs adaptively. Measure observed execution rather than asserting weights.

## Model and properties

Model only facts independently known from inputs, successful results, and documented semantics. Update ghost balances/counters only after successful calls; don't copy the same potentially broken contract value into both expected and actual values. Account for fees, shares, external transfers, accrued interest, and rounding using explicit units.

Global properties belong in invariant checks; action-specific postconditions compare pre/post state immediately after the relevant action. Give assertions stable property IDs. For relations requiring paired operations, use isolated exploratory checks or explicit lifecycle rules with tracked obligations so a probe does not silently alter subsequent state.

Source: [Hypothesis stateful testing](https://hypothesis.readthedocs.io/en/latest/stateful.html).
