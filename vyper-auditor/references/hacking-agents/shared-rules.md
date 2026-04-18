# Shared Scan Rules

## Reading

Your bundle has two sections:

1. **Core source** (inline) — read in parallel chunks (offset + limit), compute offsets from the line count in your prompt.
2. **Peripheral file manifest** — file paths under `# Peripheral Files (read on demand)`. Read only those relevant to your specialty.

When matching function names, check both `function_name` and `_function_name` (Vyper internal-function convention), and special-name dunder functions (`__init__`, `__default__`).

## Vyper language mapping

Attack-vector descriptions and patterns may name Solidity constructs. Map them to the equivalent Vyper surface:

- `modifier` / `onlyOwner` → function-level guards (`assert msg.sender == self.owner`, role-mapping checks, snekmate `Ownable` / `AccessControl` modules)
- `nonReentrant` → `@nonreentrant("...")` (≤0.3.x, single-key) or `@nonreentrant` (0.4+, single global lock)
- `unchecked { ... }` → `unsafe_add` / `unsafe_sub` / `unsafe_mul` / `unsafe_div` / `pow_mod256`
- `delegatecall` → `raw_call(target, data, is_delegate_call=True)`
- `staticcall` → `raw_call(target, data, is_static_call=True)`
- `abi.encodePacked` → `concat(...)`
- `abi.encode` / `abi.decode` → `_abi_encode(...)` / `_abi_decode(data, type)`
- `address(0)` → `empty(address)`
- `type(uint256).max` → `max_value(uint256)`
- `keccak256(abi.encodePacked(...))` → `keccak256(concat(...))`
- `selfdestruct` → does not exist in Vyper 0.4+. Older versions could call it via `raw_call`; flag if found.
- `new Foo(...)` / clones → `create_minimal_proxy_to`, `create_from_blueprint`, `create_copy_of`
- `IERC20(token).transfer(...)` returning bool → in Vyper, callers must check the bool explicitly OR use `raw_call` with `default_return_value=True` (which masks empty returns); both shapes are exploitable when misused
- `external` / `internal` / `view` / `pure` / `payable` → matching `@external` / `@internal` / `@view` / `@pure` / `@payable` decorators
- Modules — `uses:`, `initializes:`, `exports:` (Vyper 0.4+) replace inheritance / `using ... for ...`

## Cross-contract patterns

When you find a bug in one contract, **weaponize that pattern across every other contract in the bundle.** Search by function name AND by code pattern. Finding native/ERC20 confusion in `ContractA.on_revert` means you check every other contract's `on_revert` — missing a repeat instance is an audit failure.

After scanning: escalate every finding to its worst exploitable variant (DoS may hide fund theft). Then revisit every function where you found something and attack the other branches.

## Do not report

Admin-only functions doing admin things. Standard DeFi tradeoffs (MEV, rounding dust, first-depositor with `MINIMUM_LIQUIDITY`). Self-harm-only bugs. "Admin can rug" without a concrete mechanism. Vyper-style notes: bounded `for x in range(N)` loops are NOT a DoS finding by themselves.

## Output

Return structured blocks only — no preamble, no narration. Exception: vector scan agent outputs its classification block first.

FINDINGs have concrete, unguarded, exploitable attack paths. LEADs have real code smells with partial paths — default to LEAD over dropping.

**Every FINDING must have a `proof:` field** — concrete values, traces, or state sequences from the actual code. No proof = LEAD, no exceptions.

**One vulnerability per item.** Same root cause = one item. Different fixes needed = separate items.

```
FINDING | contract: Name | function: func | bug_class: kebab-tag | group_key: Contract | function | bug-class
path: caller → function → state change → impact
proof: concrete values/trace demonstrating the bug
description: one sentence
fix: one-sentence suggestion

LEAD | contract: Name | function: func | bug_class: kebab-tag | group_key: Contract | function | bug-class
code_smells: what you found
description: one sentence explaining trail and what remains unverified
```

The `group_key` enables deduplication: `ContractName | function_name | bug_class`. Agents may add custom fields.
