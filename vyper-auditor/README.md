# Vyper Auditor

A parallel security review for Vyper contracts: focused findings in minutes, before
you ship a change.

Built for:

- **Vyper developers** who want a security pass before a commit or deployment
- **Security researchers** who want structured attack coverage before manual review
- **Protocol teams** who need an additional, evidence-driven review of `.vy` code

It is not a substitute for a professional audit. Use it to surface concrete paths
worth fixing or investigating, then test and review the result.

## What it covers

The auditor coordinates 12 independent attack lenses:

1. Math and precision
2. Access control and module initialization
3. Economic security and token behavior
4. Execution traces and transaction interleaving
5. Invariants and conservation laws
6. Periphery, interfaces, encoders, and helpers
7. First-principles assumption breaking
8. Function and branch asymmetry
9. External boundaries and raw-call behavior
10. Numerical gaps across precision, invariants, and boundaries
11. Trust gaps across authority, economics, and asymmetry
12. Flow gaps across execution, periphery, and protocol intent

It also accounts for Vyper-specific semantics: compiler/pragma context, global and
file-scoped nonreentrancy, modules and `exports:`, `extcall`/`staticcall`,
`raw_call`, `default_return_value`, `@raw_return`, blueprint factories,
`raw_create`, transient storage, checked conversions, and `decimal` precision.

## Usage

```bash
# Review all in-scope Vyper contracts in the repository
/vyper-auditor

# Review specific contracts only
/vyper-auditor src/vault.vy src/factory.vy

# Save the terminal report as Markdown as well
/vyper-auditor --file-output
```

Target the contracts you changed when possible. A narrower scope gives every agent
more context for the code that matters. Run a second independent pass before a
high-stakes deployment: model output is non-deterministic, and different passes can
surface different attack paths.

## Scope and limitations

By default the skill excludes tests, mocks, interfaces, and `lib/` directories from
finding scope. Agents can still inspect those files to confirm an interface,
dependency behavior, deployment configuration, or testable attack path.

The best results are usually on roughly 2,500 lines of Vyper or less. Past 5,000
lines, split the review by module or hot contract. The skill is strongest at
concrete code-level paths and weaker at missing specifications, off-chain
assumptions, governance/game theory, and novel cross-protocol composition. Human
review, adversarial tests, formal invariants, bug bounties, and monitoring remain
essential.
