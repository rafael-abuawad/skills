# Helper commands

Use the project's Python environment and `python3 {SKILL_PATH}/scripts/fyzz.py --help` as the exact CLI reference. Every subcommand takes `PROJECT_ROOT`; consistently pass `--suite-dir test/fuzz --meta-dir fuzz_data --framework auto` or resolved overrides. Never interpolate untrusted input into shell code.

| Command | Purpose |
| --- | --- |
| `inspect` | Detect project framework, environment, configuration, and missing dependencies. |
| `inventory` | Normalize compiler/framework artifacts into `contracts.json`; repeat `--artifact PATH` for explicit artifacts. |
| `scaffold` | Create an isolated Python package and metadata configuration; refine its fail-closed protocol placeholders before campaigns. |
| `run` | Execute a generated suite with `--profile smoke|standard|extended`, optional `--timeout SECONDS`, and optional `--runner '["uv","run","ape","test"]'`. |
| `properties` | Inspect property states and source markers for reconciliation. |
| `snapshot` | Write the validated baseline to `last-run.json`. |
| `diff` | Read-only comparison against the baseline; does not repair or advance it. |

Artifacts may be normalized objects `{ "contract": "Vault", "source": "src/Vault.vy", "abi": [...] }` or supported standard compiler/framework artifacts. If native artifacts are not understood, export normalized JSON using their public API. Retain the original artifact and compiler/version provenance. ABI inputs alone cannot recover Vyper dynamic bounds.

Helpers do not synthesize deployment semantics, select trustworthy invariants, repair handwritten actions, or prove compatibility. Agents perform those steps and verify results. Do not claim a helper flag exists without checking its help output.

## Output ownership

`{SUITE_DIR}` contains executable Python setup, strategies, model, actions, properties, machine, runtime, conftest, entrypoint, and reproduction tests. `{META_DIR}` contains `fyzz.json`, inventories, `selection.json`, protocol notes, `PROPERTIES.md`, property plans, profiles/effective settings, logs, database, traces, reports, coverage when supported, backups, and `last-run.json`.

Reuse saved paths on maintenance runs. Preserve an existing project-root `PROPERTIES.md`; the Fyzz specification lives in its metadata directory. Scaffold collisions require inspection and selective merging, never blanket regeneration.
