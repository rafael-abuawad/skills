---
name: vyper-best-practices
description: >
  Vyper contract guidance for writing, reviewing, or refactoring `.vy` and `.vyi` code.
  Use for compiler-compatible syntax, type choices such as `flag`, module composition,
  external calls, revert handling, and security patterns.
---

# Vyper Best Practices

## Workflow

1. Resolve the compiler and EVM targets from the source pragma and project configuration. Preserve them; do not silently widen a version constraint or introduce a feature the target compiler lacks.
2. Use the latest Vyper documentation to discover current idioms, then check version-dependent syntax against the target compiler's documentation. The `latest` docs describe development work and may include unreleased features.
3. Write native Vyper syntax. Compile complete generated contracts with the selected compiler when it is available. If compilation is unavailable, say what was checked and what remains unverified; mark fragments and version-gated examples clearly.
4. Finish when every generated code example is either compiler-checked for its declared target or explicitly marked as a fragment or version-dependent.

Vyper favors module composition. Reuse implementation through imported modules; use interfaces to describe calls to other contracts.

## Type and naming choices

- Use `flag` for named roles, permissions, or options that benefit from typed bitset operations. Use `in` to check whether any requested bit is set and `==` to compare the full flag value.
- Use `constant` for fixed compile-time values such as limits and selectors, `immutable` for values set once at deployment, and ordinary state for values that change.
- Use `bool` for a single true/false value; do not encode it as a flag or integer mask.
- Follow the project's naming conventions. Otherwise, use snake_case for local module, function, and state names; preserve exact ABI names when implementing an external standard; PascalCase for types and interfaces; UPPER_SNAKE_CASE for constants; and a leading underscore for internal helpers and state.

## Current Vyper patterns

- Use `@deploy` for `__init__`. Add `@payable` only when deployment should accept ETH.
- Use explicit `extcall` for state-changing interface calls and `staticcall` for view calls.
- Use `@external` for ABI entrypoints. State mutability defaults to nonpayable; declare `@view`, `@pure`, or `@payable` when appropriate. `@internal` is optional in recent Vyper versions; include it when it improves clarity or matches the project.
- Bound variable-length loops with `range(stop, bound=N)`. Keep Vyper's checked arithmetic unless a documented invariant justifies an unchecked operation.
- Choose `@nonreentrant` or the file-level nonreentrancy pragma after reviewing callbacks and state invariants. The lock is global; do not stack calls through multiple locked entrypoints.
- Use an access-control module such as snekmate when it fits the project and target version; do not add a dependency by default.

## Reverts and developer feedback

Vyper `assert` and `raise` may include an on-chain reason string, but the string is optional. Do not default to an on-chain string solely for developer diagnostics; keep one when transaction users or integrators need it. For Titanoboa projects, an optional `# dev: "..."` comment on an assertion can provide a clearer off-chain test failure without adding an on-chain string. This comment is a Titanoboa convention, not Vyper runtime syntax; use it selectively.

## Documentation and layout

Write useful NatSpec for public interfaces and functions, but do not require every tag on every function. NatSpec tags are optional, and the compiler does not parse internal-function docstrings. Group pragmas, imports, module declarations, types, state, events, and functions consistently with the project. Vyper does not require a fixed blank-line count between every top-level declaration.

For details and compiler-checked examples, read [reference.md](reference.md). Treat official Vyper documentation as the language authority; use Titanoboa documentation for its development-only revert annotations and ecosystem lists to discover libraries and tools.
