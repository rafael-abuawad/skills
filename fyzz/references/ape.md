# ApeWorX adapter

Detect `ape-config.yaml` or Ape configuration in `pyproject.toml`, plus Ape-style deployment/fixtures. Require the project's Ape, Vyper compiler plugin, Hypothesis, pytest, and configured local provider. Use existing dependency pins and `ape compile`; run through `ape test` (including its project environment prefix).

Use the `project`, `accounts`, and `chain` fixtures when available. Pass a deployment factory into `run_state_machine_as_test` so fixtures are resolved by pytest but deployment happens within each machine's isolation. Use `accounts` from tests or `accounts.test_accounts` outside tests. Supply explicit `sender=actor` and transaction value for each operation.

Use the generated adapter’s explicit `chain.snapshot()` / `chain.restore(snapshot)` context before deploying; restore in teardown and on construction errors. Ape 0.8.51 `chain.isolate()` can suppress exceptions and its pending-timestamp reset produced a replay failure during validation; the adapter deliberately uses the public snapshot APIs directly. Verify timestamps as part of project setup and record intentional time advances. Pytest function isolation surrounds the whole test, not each Hypothesis example. A deployment fixture object may be reused only when its state belongs to a verified snapshot; never carry mutable Python bookkeeping across examples.

Use public project contract containers/artifacts to obtain compiler ABI and source provenance. Expected rejection cases should use the project's `ape.reverts(...)` conventions with the narrowest available reason/type. Keep Python postconditions outside revert contexts.

Verify provider support for snapshot/restore and time/block controls with a small local test. If unsupported, report the provider blocker rather than running examples against shared state. Keep live account signing and remote broadcasts outside default suite execution.

Sources: [Ape testing and fixtures](https://docs.apeworx.io/ape/stable/userguides/testing.html), [chain manager isolation](https://docs.apeworx.io/ape/stable/methoddocs/managers.html), [test accounts](https://docs.apeworx.io/ape/stable/userguides/accounts).
