---
name: fyzz-convert
description: Implement pending English-language Fyzz properties as Python Hypothesis invariants and action postconditions in an existing Vyper fuzz suite. Use for fyzz-convert or requests to implement selected Fyzz property IDs.
---

# Fyzz Convert

Convert pending properties in `{META_DIR}/PROPERTIES.md` into executable assertions in an existing Fyzz suite. Hypothesis is the only fuzzing engine; reuse the suite's ApeWorX, Titanoboa, or Moccasin integration.

## Resolve the suite

`PROJECT_ROOT` defaults to the working directory. Resolve `SUITE_DIR` and `META_DIR` from explicit arguments, then the existing `fuzz_data/fyzz.json`; defaults are `test/fuzz` and `fuzz_data`. A custom metadata location must be supplied when it cannot be discovered unambiguously. Locate the sibling `fyzz` directory relative to this skill and use its `scripts/fyzz.py` helper.

Read [property conventions](../fyzz/references/properties.md) and [maintenance rules](../fyzz/references/maintenance.md). Load the resolved `fyzz.json`, property spec, property plan, setup, actions, model state, and affected Vyper source. If the suite or spec is absent, report that prerequisite and use [Fyzz](../fyzz/SKILL.md) to generate it only when generation is within the user's request.

## Reconcile and implement

1. Run the read-only reconciliation:
   ```bash
   python3 "{FYZZ_PATH}/scripts/fyzz.py" properties "{PROJECT_ROOT}" --suite-dir "{SUITE_DIR}" --meta-dir "{META_DIR}"
   ```
   Inspect markers and actual call wiring; a marker alone does not prove an assertion executes. Report duplicate IDs, unknown code IDs, implemented entries without assertions, and changed specs before editing those entries.
2. Select the IDs requested by the user, or all `[ ]` entries by default. Leave `[-]` and `[~]` entries untouched unless the user explicitly requests their reconsideration. For missing, conflicting, or ambiguous IDs, report the conflict without guessing the intended property.
3. Back up files that will change using the maintenance rules. Implement global invariants (`GL-NN`) and action postconditions (`SP-NN`) with docstrings beginning `fyzz: GL-01` or `fyzz: SP-01`, substituting the actual ID. Reuse model state and snapshots, update ghost state only after successful calls, and wire specific properties into their applicable actions. Preserve unrelated assertions and handwritten actions.
4. Test the affected assertions and run the suite's smoke profile through its configured framework. Show that a property can fail when its guarantee is violated, using a controlled model perturbation or a temporary faulty fixture when practical. An assertion skipped by an unmet precondition is not validated.
5. Mark only validated, wired implementations `[x]`. Keep unresolved entries `[ ]` with the missing evidence, state, or integration documented in the property plan. Limit targeted repair to three cycles and report remaining blockers.
6. Rerun reconciliation. Refresh the source snapshot only if relevant source drift has been reconciled and validation succeeded; otherwise preserve the baseline for `fyzz-sync`.

Report implemented IDs, pending or conflicting IDs, changed files, exact validation commands and outcomes, and any untested framework behavior. Report property failures separately from harness errors; a `SHOULD-HOLD` tag alone does not establish a protocol bug.
