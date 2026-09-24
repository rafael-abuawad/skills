# Property contract and maintenance

The canonical specification is `{META_DIR}/PROPERTIES.md`. Keep one checkbox entry per stable identifier:

```markdown
- [ ] GL-01 SHOULD-HOLD — Assets cover redeemable claims.
  Evidence: docs/accounting.md, section Solvency; src/Vault.vy.
  Dependencies: src/Vault.vy; withdraw(uint256); deposit(uint256).
  Implementation: properties.py::check_solvency; machine.py invariant hook.
  Assumptions: no fee-on-transfer backing token; liability rounding documented below.
```

`GL-NN` identifies global invariants; `SP-NN` identifies action-specific postconditions. Record priority and precise mathematical relation/units in `property-plan.md`. IDs persist across wording changes and are not reused for unrelated guarantees.

| State | Meaning |
| --- | --- |
| `[ ]` | Pending implementation or blocked; explain the blocker. |
| `[x]` | Assertion and execution wiring implemented and validated. |
| `[-]` | Explicitly disabled; record user intent/reason. |
| `[~]` | Quarantined because source/spec drift invalidated confidence; not an active assertion. |

Use discoverable Python markers `# fyzz:property GL-01` immediately above the implementing function; include the ID in assertion messages. Record wiring associations in the plan. A marker alone does not prove a property executes, and a checkbox is not test evidence. Inspect actual call sites, decorators, and test outcomes.

`SHOULD-HOLD` requires a cited documented guarantee, standard, or exact identity with stated domain. `EXPLORATORY` denotes an inferred expectation. Both may contain harness errors: reproduce, validate the model, and confirm assumptions before triage. A clean SHOULD-HOLD violation after that review is a confirmed guarantee violation; severity requires separate impact analysis. Exploratory violations remain leads until the intended behavior is established.

## Conversion

Select requested pending IDs or all `[ ]` entries by default. Reconcile current Python markers, wiring, source, and spec before editing. Disabled and quarantined entries need explicit reconsideration; do not silently reactivate them. Implement shared ghosts/snapshots first, then assertions and wiring through one integrating writer. Validate targeted actions and smoke tests before changing `[ ]` to `[x]`. Retain the spec text and report unexplained mismatches.

## Synchronization

The read-only default compares the last validated snapshot against source hashes, ABI signatures, selected actions, property text/associations, generated code, configured paths, and versions. A source body change matters even when ABI signatures match. Track added, removed, changed, and ambiguous dependencies; treat uncertain associations conservatively.

For `--apply`, preserve handwritten code, make backups of affected files under metadata, and change only affected actions/strategies/setup. Quarantine properties affected by semantic or signature drift: switch their spec to `[~]` and remove/guard their active wiring while retaining the implementation and reason for review. A checkbox edit alone does not quarantine executable assertions. Do not globally disable all properties merely because one contract changed.

Compile and validate changed actions, unaffected invariants, and any property deliberately re-established. Only then refresh the baseline. On failure retain the old baseline and report partial edits plus backup paths. Added functions remain explicit selections to assess against protocol understanding; source removal is not permission to discard handwritten code blindly.
