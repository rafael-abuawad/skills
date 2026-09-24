---
name: fyzz-sync
description: Detect and reconcile drift between Vyper sources and an existing Fyzz Hypothesis suite. Use for fyzz-sync, changed contract signatures, stale Fyzz properties, or requests to update an existing harness after source edits.
---

# Fyzz Sync

Compare an existing Fyzz suite with its validated baseline. Default to a read-only drift report. `--apply` authorizes surgical suite updates by the agent; it is not an option passed to the diff helper.

## Inspect drift

`PROJECT_ROOT` defaults to the working directory. Resolve `SUITE_DIR` and `META_DIR` from explicit arguments, then the existing `fuzz_data/fyzz.json`; defaults are `test/fuzz` and `fuzz_data`. Supply a custom metadata location when discovery is ambiguous. Locate the sibling `fyzz` directory relative to this skill.

Read [maintenance rules](../fyzz/references/maintenance.md) and [property conventions](../fyzz/references/properties.md). Read the resolved configuration, `last-run.json`, current sources, contract inventory, actions, and property spec.

Run:

```bash
python3 "{FYZZ_PATH}/scripts/fyzz.py" diff "{PROJECT_ROOT}" --suite-dir "{SUITE_DIR}" --meta-dir "{META_DIR}"
python3 "{FYZZ_PATH}/scripts/fyzz.py" properties "{PROJECT_ROOT}" --suite-dir "{SUITE_DIR}" --meta-dir "{META_DIR}"
```

A missing baseline is not a clean result: explain that historical drift cannot be determined. In read-only mode, report added and removed contracts/functions, signature changes, source-only changes, property/spec drift, framework version changes, and affected actions. Inspect source-only edits for changed guarantees and dependencies even if the ABI is identical. Do not compile, refresh artifacts, run campaigns, or write reports during the read-only pass.

## Apply requested repairs

When `--apply` or an equivalent explicit update request is present:

1. Back up affected files before editing. Preserve the old snapshot and inventory as comparison evidence. Recompile with the project's existing framework, refresh its normalized inventory through Fyzz's inspection workflow, and verify signatures against current artifacts before generating calls.
2. Retain selected entry points unless removed or invalidated. Present newly added entry points with the protocol-based selection rationale. Update only affected actions, strategies, deployment setup, and model dependencies; preserve handwritten code and unrelated selections.
3. Quarantine stale properties as `[~]` with a reason and affected dependencies. Remove their active invariant decoration or invocation while preserving their implementation and evidence for review. An unchanged signature does not establish semantic validity. Keep explicitly disabled `[-]` entries disabled.
4. Reimplement quarantined properties only when the current source/spec establishes their meaning. Pending new properties can be implemented using [Fyzz Convert](../fyzz-convert/SKILL.md). Apply its validation requirements before moving an entry to `[x]`.
5. Validate collection, affected actions, isolation, and the smoke profile; run deterministic reproductions relevant to changed flows. Limit targeted repair to three cycles. Preserve the baseline on failure, with a precise partial-change report.
6. Reconcile all known drift, record unresolved quarantine and excluded actions, then refresh the baseline after successful validation:
   ```bash
   python3 "{FYZZ_PATH}/scripts/fyzz.py" snapshot "{PROJECT_ROOT}" --suite-dir "{SUITE_DIR}" --meta-dir "{META_DIR}" --refresh
   ```
   For an absent baseline, omit `--refresh` only after inspecting the entire existing suite and validating it. Report this as initialization, not proof of synchronization with an earlier source version.

Report the applied changes, intentionally excluded actions, quarantined IDs, backup location, exact validation outcomes, and whether the baseline was refreshed. A refreshed baseline records the reviewed state, including explicit quarantine; it does not mean every source path or property is covered.
