# Titanoboa adapter

Use the project's Python environment with `titanoboa` (import `boa`), Hypothesis, pytest, and its compatible Vyper version. Run through the project's Python/pytest command. Reuse `boa.load`/`boa.loads` deployment helpers and compiler artifacts matching the actual project version.

Enter `boa.env.anchor()` before setup for every machine; it snapshots VM state and restores it on exit. Close isolation on construction errors and in teardown. Create fresh actors/model containers for each example. Use `boa.env.prank(actor)` for caller scopes and `boa.env.set_balance` to fund actors as needed; restore caller context after calls.

For deliberate rejection cases use `boa.reverts(...)` around only the contract call, with a verified reason when available. Run model updates and assertions outside that context. Accepted valid actions should propagate any unexpected `BoaError`. Preserve time/block changes explicitly in replay records; verify the installed API before implementing them.

ABIs are available on compiled contract/deployer objects; export those rather than guessing signatures. Read source/compiler type metadata for bounded `Bytes`, `String`, and `DynArray` strategies. Local tests should avoid network environment replacement unless the user explicitly requested a fork.

Sources: [environment API](https://titanoboa.readthedocs.io/en/latest/api/env/env/), [official repository](https://github.com/vyperlang/titanoboa). Consult the installed version for compilation and coverage APIs; the existence of Python coverage output does not establish Vyper coverage.
