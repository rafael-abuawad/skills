# Fyzz maintenance

Read this reference when converting properties, reconciling source drift, or establishing a validated snapshot. `properties` and `diff` are inspection helpers; agent edits perform conversion and synchronization.

## Configuration and baseline

Resolve paths before reading or writing. Explicit user paths take precedence over stored configuration; otherwise use `fuzz_data/fyzz.json`, with `test/fuzz` and `fuzz_data` as defaults for new suites. If metadata was relocated, require an explicit location or an unambiguous existing configuration rather than creating a second metadata directory.

`last-run.json` records source content hashes, compiler/framework ABI signatures, property associations and implementation hashes, framework versions, and configured suite/metadata paths. A source hash change with an identical ABI still requires semantic review. Compiler artifacts may be stale: in a read-only report state that limitation; during apply, rebuild before updating the inventory. Framework version changes require checking deployment, isolation, exception handling, and compiler compatibility before accepting a new baseline.

Use `snapshot PROJECT_ROOT --suite-dir SUITE_DIR --meta-dir META_DIR` to initialize a missing baseline, or append `--refresh` to replace one. These commands capture state; they cannot prove tests passed. Run them only after reviewing drift and completing validation. Record the validation command and result with the maintenance report.

## Property reconciliation

| Spec status | Meaning | Executable state |
|---|---|---|
| `[ ]` | Pending implementation or validation | Not counted as implemented |
| `[x]` | Implemented, wired, and validated | Active assertion |
| `[-]` | Explicitly disabled | Excluded from active assertion paths |
| `[~]` | Quarantined after drift | Excluded until reviewed and validated |

The stable ID links an English guarantee, evidence, source dependencies, and an assertion. Python assertion functions use a docstring whose first line begins `fyzz: GL-NN` or `fyzz: SP-NN`. Global functions must be reached by Hypothesis invariant evaluation; specific functions must be reached by the relevant action after its successful operation. Markers support discovery, not proof of execution.

Report these conflicts rather than silently resolving them: duplicate IDs; unknown IDs in Python; `[x]` without an active assertion; changed property text with old implementation; active `[-]` or `[~]` assertions; deleted spec entries with remaining implementation. A renamed property retains its ID when its guarantee is unchanged. A different guarantee needs a new ID or an explicit reviewed revision.

For quarantine, preserve code and the previous specification. Remove the affected assertion's active decorator or call and annotate the reason, changed dependencies, and required review in the property plan. Preserve shared model updates needed by other active properties. Re-enable only after verifying the current guarantee and executing its assertion path successfully.

## Surgical edits and backups

Before the first mutation, create a unique `{META_DIR}/backups/<UTC-timestamp>-<unique-suffix>/` directory. Copy each affected existing file into it, preserving its project-relative path. Include configuration, selections, property spec, inventory, and the old snapshot if they will change. Record newly created paths separately so rollback can distinguish them from copied files. Do not replace or delete user files outside the affected suite/metadata set.

Adapt the smallest affected portion of an action or property. Retain handwritten implementations, comments explaining assumptions, excluded selections, and custom deployment fixtures. Removed functions require checking every call site and property dependency. Changed signatures require checking overload identity, arguments, return interpretation, bounds, and callers. Source-only changes require reviewing state transitions, access controls, arithmetic/rounding, and guarantees used by affected assertions.

When a safe adaptation cannot be established, disable the affected action or quarantine its properties with a concrete reason. Report lost reachability explicitly. Avoid whole-suite regeneration as a repair technique.

## Validation and completion

Use the project's recorded environment and framework runner. Validate syntax/collection, then targeted action/property behavior, then the smoke campaign. Existing deterministic reproductions must still exercise the same property; a different revert or setup error is not a successful reproduction. For a fixed defect, update the reproduction into a regression assertion that passes when the guarantee holds.

A successful smoke run does not alone prove a property was exercised. Review action counters, preconditions, and lifecycle transitions; execute a deterministic targeted path when coverage of the changed assertion is unclear. Keep missing tooling and untested integrations visible. After three unsuccessful targeted repairs, stop and report the specific blocker without overwriting the baseline.

Refresh a baseline only after every detected change is accounted for through adaptation, reviewed exclusion, or documented quarantine, and the remaining active suite validates. Preserve original source/ABI evidence and user edits throughout; a snapshot update must never erase unexplained drift.
