# Shared Scan Rules

## Bundle contents and reading discipline

Your bundle concatenates: all in-scope source, the senior-auditor SOP,
Vyper-language semantics, your specialty, these rules, and the report-language rules. When memory is
on and records exist, known findings follow last. Read it fully once
before producing results. The bundle is the initial source of truth; do not
re-read in-scope files for the initial pass.

You may make targeted reads only to investigate a plausible cross-file path or to
obtain necessary context from out-of-scope interfaces, imported dependencies,
deployment/configuration files, or tests. Do not use a missing test, deployment
intent, or a likely configuration as proof that a concrete code path is safe.

Function names are Vyper snake_case. Check `function_name`, `_function_name`,
public getters, module exports, and `__init__` / `__default__` explicitly. For each
file, record its Vyper pragma and nonreentrancy setting before relying on a language
property; see `vyper-language.md`.

## Mandatory mental-tool markers

The senior-auditor tools are not optional. When a trigger fires while reading source,
emit the required marker in your working text before continuing. Do **not** place
these markers inside a FINDING or LEAD block; they are evidence of review depth.

| Trigger | Required marker | Content |
| --- | --- | --- |
| You open a contract, module, or function | `[Feynman: <name>]` | Explain it in plain language. Identify the first assumption that cannot be explained without Vyper jargon. |
| A line's purpose or assumption is not immediately clear | `[Socratic: <file:line> — why?]` | Ask the question that reaches the implicit belief, not a restatement of the code. |
| A path or guard looks clean or sufficient | `[Inversion: <function>]` | Give three concrete attacker moves: caller, values, state, callback, or ordering. |

Triggers are mandatory. Extra markers are welcome. Markers prove reasoning depth,
not report volume.

## Cross-contract propagation

When one instance of a root cause is found, search every in-scope contract and
first-party module for the code pattern and semantic equivalent. A fee-on-transfer
accounting bug, a missing `extcall` result assertion, a raw-call response decoder,
or an unprotected exported module function rarely appears exactly once.

Escalate every candidate to its worst demonstrated variant. A DoS may mask a fund
lock, a state inconsistency may unlock a withdrawal, and a local reentrancy issue
may be cross-contract. Then return to every affected function and attack its other
branches.

## Do not report

Do not report admin-only operations performing their documented administrative role,
standard DeFi tradeoffs (ordinary MEV, bounded rounding dust, a first-depositor
tradeoff already mitigated by minimum liquidity), self-harm-only behavior, missing
events, naming/style/NatSpec issues, compiler/linter warnings, or a fixed small
Vyper loop by itself. A compiler advisory is reportable only if the deployed or
reproducibly configured Vyper version is affected and the affected construct reaches
material impact.

## Output

Return structured blocks only after your mental-tool markers. Do not add a prose
summary.

A **FINDING** has a complete, unguarded, materially harmful attack path. A **LEAD**
has a concrete code smell and partial path, but some necessary fact is unverified.
Default to a lead rather than dropping a valuable trail or inflating confidence.

Every FINDING needs a `proof:` field containing actual source citations, concrete
numbers, or a state/call trace. No proof means LEAD. One vulnerability per item;
different fixes are different items even when they are in the same function.

```
FINDING | contract: src/vault.vy | function: function_name | bug_class: kebab-tag | group_key: src/vault.vy | function_name | bug-class
path: caller → entry point → state change / external interaction → impact
proof: concrete values, exact trace, or quoted source demonstrating the exploit
compiler_context: relevant pragma / deployment version when language-version behavior matters
description: one sentence
fix: one-sentence safe minimal suggestion

LEAD | contract: src/vault.vy | function: function_name | bug_class: kebab-tag | group_key: src/vault.vy | function_name | bug-class
code_smells: precise suspicious code or missing invariant
unverified: the exact precondition, deployment fact, or external behavior still needed
compiler_context: relevant pragma / deployment version when language-version behavior matters
description: one sentence explaining the trail
```

Use `compiler_context` only for a version-sensitive claim. The `group_key` format is
strict: `repo-relative.vy | function_name | bug-class`. Agents may add specialty fields, but
must retain all required fields.

## Identity and prior findings

`contract` is the repository-relative path, including `.vy`, exactly as the source
heading spells it. Two files with the same basename are different contracts.
`function` is its original identifier: dunder names stay intact, public getters
use the variable name, and file-level findings use `__module__`. Attribute a
module's code defect to that module; attribute an export or binding defect to the
host. Describe host/module context in the proof. The orchestrator normalizes keys;
agents keep source spelling in these fields.

When the bundle includes known findings, reuse a listed bug-class label for the
same defect in the same file and function. Spend reading effort on new ground,
but report every bug you find in full, including listed bugs.

## Language

Write descriptions and fix suggestions in Simplified Technical English per
`report-language.md`: active voice, one sentence of at most 25 words, a named actor
and effect. Preserve identifiers, bug-class labels, quoted source, and diff code.
Proofs retain concrete values, traces, and source citations.
