# Moccasin adapter

Detect `moccasin.toml` or the project's Moccasin configuration. Moccasin uses Titanoboa execution, but retain its project dependency resolution, imports, network configuration, and runner. Require the project's `mox`, Hypothesis, pytest, and compatible compiler/dependencies. Run the existing compile flow and execute through `mox test` with the repository's environment prefix.

Reuse deployment scripts and configured dependencies. Read [Titanoboa isolation](boa.md) for per-example anchors, actor contexts, reverts, and ABI extraction. Initialize Moccasin context through its runner before accessing named contracts or configuration; a bare pytest invocation may lose project initialization.

Confirm the selected network is the project's local test network. Explicit fork requests may use the project's pinned fork setup; record fork identity/block and external prerequisites. Do not inherit a live network accidentally from a deployment default.

Read `mox test --help` in the installed version when constructing runner arguments: option forwarding and test paths depend on that version. Preserve framework handling of project paths rather than overwriting root pytest configuration. If coverage is requested, inspect whether the report attributes measured lines/branches to `.vy` sources before labeling it contract coverage.

Sources: [Moccasin test CLI](https://cyfrin.github.io/moccasin/cli_reference/test.html), [Moccasin quickstart](https://cyfrin.github.io/moccasin/quickstart.html), [official repository](https://github.com/Cyfrin/moccasin).
