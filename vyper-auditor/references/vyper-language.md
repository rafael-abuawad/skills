# Vyper Security Semantics and Compiler Baseline

Use this reference before classifying a Vyper finding. Vyper removes some Solidity
footguns, but it does not remove EVM, protocol, or compiler-version risk. Do not
report a language property as a vulnerability; attack the code that opts out of or
misuses that property.

## 1. Establish the deployed compiler context first

Create a short private ledger for every in-scope file:

- Read `# pragma version` in the file and any imported first-party module.
- Corroborate it from `moccasin.toml`, `pyproject.toml`, lockfiles, CI, deployment
  scripts, or verified deployment metadata when available.
- Record `# pragma evm-version`, `# pragma nonreentrancy on|off`, optimizer and
  experimental/Venom settings where present.
- A compiler-specific issue is a finding only when the deployed or reproducibly
  configured compiler falls inside the affected range. If the version is unknown,
  emit a lead explaining exactly what artifact/version must be confirmed.

**Stable baseline:** Vyper `0.4.3` is the latest stable release covered by this
reference. `0.5.0` alpha releases are not a production-safety baseline. Do not
assume a source file using a broad pragma was compiled with the installed local
Vyper binary.

### Material version boundaries

| Range | Audit consequence |
| --- | --- |
| `<=0.3.10` | Treat the compiler version as high-risk legacy context. Several fixed code-generation issues affect evaluation order, `slice`, `sqrt`, `raw_call`, `create_from_blueprint`, `raw_log`, bounds checks, and returndata/memory handling. Verify the exact GHSA and deployed artifact before reporting. |
| `0.4.0` | Major module-system release. `@nonreentrant` becomes one global lock (keys are no longer supported). It is affected by the 0.4.0-only AugAssign, list-iterator evaluation, `sqrt` rounding, and precompile-success advisories fixed in 0.4.1. |
| `0.4.1` | Fixed the 0.4.0 advisories and made return-data checks robust even when `skip_contract_check=True`; interface/import and `IERC4626` changes can make copied interfaces semantically wrong. |
| `0.4.2` | Adds `# pragma nonreentrancy on` and `raw_create()`. It fixes zero-length `concat` side-effect elision and zero-length `slice` side-effect elision present before 0.4.2. |
| `0.4.3` | Adds `@raw_return`, creating a deliberate raw-proxy surface. It changes the default EVM version to Prague. |

Relevant advisories include: `GHSA-3vcg-j39x-cwfm` (`slice`, `<0.4.2`),
`GHSA-qhr6-mgqr-mchm` (`concat`, `<0.4.2`), `GHSA-4w26-8p97-f4jp`
(AugAssign, `<=0.4.0`), `GHSA-h33q-mhmp-8p67` (list iteration, `<=0.4.0`),
`GHSA-2p94-8669-xg86` (`sqrt` rounding, `<=0.4.0`), and
`GHSA-vgf2-gvx8-xwc3` (precompile-call success, `<=0.4.0`). Earlier compiler
advisories are not automatically irrelevant: use the exact version range from the
Vyper security advisory before asserting exploitability.

## 2. Reentrancy is global only when it is actually enabled

- In Vyper `>=0.4.0`, `@nonreentrant` uses one global lock. A protected mutable
  entry point blocks callbacks into every other protected entry point, but it does
  **not** protect an unannotated external function, an unannotated public getter,
  or code in a separately imported file.
- In Vyper `<0.4.0`, `@nonreentrant("key")` locks only functions sharing that key.
  Map keys across all entry points; a callback through a different key remains a
  candidate.
- Since `0.4.2`, `# pragma nonreentrancy on` protects external functions and public
  getters in that **file** (except constant/immutable getters). `@reentrant` and
  `reentrant(T)` getters deliberately opt out. Imported modules keep their own
  pragma; the pragma does not propagate through imports.
- A view function can expose transitional state during a callback. A protected
  mutable function can protect a view function from callback entry; a view function
  cannot acquire a persistent lock itself. Check price, share, collateral, and
  `total_assets`-style getters for read-only reentrancy.
- Do not rely on a 2,300-gas `send` stipend for safety. An attacker can invoke a
  payable fallback through a normal call with more gas, and transient storage makes
  old low-gas assumptions especially unsafe.
- `__default__` is a real external boundary. With nonreentrancy-on it is protected
  by default; an explicitly reentrant or legacy default function must be traced.
  A protected payable default may reject ETH callbacks, which can itself create DoS.

## 3. External-call and token semantics

### Interface calls

Vyper `0.4+` makes mutating interface calls explicit with `extcall` and view calls
with `staticcall`. These express intent; they do not make a target honest.

- `extcall IERC20(token).transfer(...)` can run arbitrary token code, including
  ERC-777-style hooks or malicious callbacks. Apply CEI and map every callback
  entry point.
- An asserted boolean result is required when the interface declares `-> bool`.
  Ignoring a false return is a state/accounting bug.
- `default_return_value=True` is an **interface-call** keyword, not a `raw_call`
  keyword. It supplies `True` only for empty returndata so no-return ERC-20 tokens
  can be supported. It does not turn a false return into true, and Vyper still
  performs the contract-existence check unless `skip_contract_check=True` is also
  set. Ensure the returned/defaulted boolean is asserted before accounting changes.
- `skip_contract_check=True` removes the `EXTCODESIZE` check. It is justified only
  by a documented, safe reason. With a no-return function it can turn an EOA or
  undeployed address into a successful no-op; with a returned value, later Vyper
  versions still check returndata size, but no-return/defaulted paths require
  special scrutiny.
- A typed interface is only an ABI promise. Verify `.vyi`/JSON interface signatures,
  return types, mutability, token decimal assumptions, and whether a `@raw_return`
  target is mistakenly called through an ABI-decoding interface.

### `raw_call`

`raw_call` is an untyped EVM call and has no automatic code, ABI, return-length, or
boolean validation.

- With `revert_on_failure=False`, it returns `success` (and response data if
  `max_outsize > 0`). A caller must check `success` before committing accounting.
- `max_outsize` is an attacker-controlled truncation boundary when the target is
  untrusted. Before `_abi_decode`, validate success, expected minimum/exact length,
  selector/domain, and all decoded values.
- `is_delegate_call=True` executes foreign code in the caller's storage context.
  Treat a mutable or user-selected target as arbitrary storage control. Audit custom
  storage layout, admin slot collision, value forwarding, and return/revert
  propagation.
- `is_static_call=True` is appropriate for reads but does not establish freshness,
  authenticity, or a truthful response. It cannot be used as a substitute for an
  oracle validity check.
- A raw call to an address without code may succeed with empty returndata. Never
  decode or treat empty bytes as a successful transfer without an explicit safe
  policy.

### Native ETH, callbacks, and forced balance changes

Trace every `send`, `raw_call(..., value=...)`, payable function, and
`__default__`. Enforce the relationship between `msg.value` and any claimed amount;
account for excess value, underpayment, and fees in every branch. Do not use
`self.balance` as proof of internal accounting: ETH can be force-fed (for example
by `SELFDESTRUCT`, CREATE2 prefunding, or protocol-level balance changes).

## 4. Modules, exports, and initialization (Vyper 0.4+)

Vyper modules replace inheritance, not the need for access-control and lifecycle
auditing.

- Map every `from ... import`, `initializes:`, `uses:`, dependency binding, and
  `exports:` declaration. Include first-party imported `.vy` modules in a targeted
  trace even when they are not part of default scope.
- `initializes:` means the importing contract owns module state and must invoke the
  module initializer during `__init__`. Check each initializer runs exactly once,
  with the intended owner, role, token, oracle, and implementation addresses.
- `uses:` gives a module access to another module's state. Verify dependency
  bindings (including walrus syntax) refer to the intended instance rather than a
  compatible-but-wrong module.
- `exports:` expands the host's external ABI. Audit exported module functions as
  host entry points: their `msg.sender`, ownership assumptions, nonreentrancy
  setting, and initialization state may differ from the caller's assumptions.
- The nonreentrancy pragma is file-scoped. A protected host does not automatically
  protect an imported module that lacks its own protection.

## 5. Factories, blueprints, raw return, and storage

- `create_from_blueprint` should use a trusted, immutable or access-controlled
  blueprint. The blueprint's ERC-5202 preamble/code offset matters: an unprotected
  callable blueprint can execute constructor-side effects when called directly.
  Check constructor arguments, supplied ETH, deterministic salts, collision/error
  handling, child initialization, and who receives/controls the new child.
- `raw_create` (0.4.2+) exposes CREATE/CREATE2 directly. If
  `revert_on_failure=False`, a zero address signals failure and must not enter
  storage or later accounting. Bind user salts to the intended creator when
  address squatting matters.
- `create_minimal_proxy_to`, `create_copy_of`, and raw delegatecall designs require
  the same implementation trust and storage-context review as proxy systems.
- `@raw_return` (0.4.3+) returns bytes without ABI encoding. It is useful for
  proxies, but every path must return the expected raw bytes and preserve success
  versus revert data. Call it with `raw_call`, not a normal ABI interface.
- `immutable` values are bytecode values set at deployment. Validate constructor
  ordering and all immutable configuration; a delegatecall proxy sees the
  implementation's immutables, not per-proxy storage.
- `transient(T)` lasts only for the transaction. Never use it for cross-transaction
  authorization, balances, nonces, or persistent accounting. A transient lock must
  be set before the call and cleared on every safe completion path; it still needs
  CEI and must not rely on the obsolete low-gas reentrancy model.

## 6. Arithmetic, data, and loop constraints

- Ordinary Vyper integer arithmetic reverts on overflow and underflow. Do not flag
  plain `+`, `-`, or `*` as missing SafeMath. Audit `unsafe_add`, `unsafe_sub`,
  `unsafe_mul`, `unsafe_div`, `pow_mod256`, bit/shift math, and unchecked
  assumptions around them instead.
- `convert(x, smaller_type)` is bounds checked; do not report it as a Solidity-style
  silent downcast. Still trace signed/unsigned boundaries, `decimal` conversion,
  bytes/integer representations, and conversions followed by unsafe arithmetic.
- `decimal` is fixed-point with 10 decimal places. Never assume it is WAD. Normalize
  token, oracle, basis-point, and decimal scales explicitly; test zero, one, max,
  and smallest nonzero values.
- `_abi_decode`, `abi_encode`, `concat`, `slice`, `extract32`, `method_id`, and
  dynamic `Bytes[N]`, `String[N]`, or `DynArray[T, N]` inputs are boundary surfaces.
  Validate semantic length/domain as well as compiler-enforced bounds.
- Vyper loops are statically bounded, but `range(stop, bound=N)` can revert if
  attacker-controlled `stop` exceeds `N`, and a permitted large bound can still
  make a critical operation unexecutable. Do not report a small fixed bound by
  itself; prove the reachable gas or liveness failure.

## 7. High-value EVM/protocol checks that Vyper still needs

Vyper does not prevent fee-on-transfer or rebasing token accounting errors,
blacklist/pause DoS, ERC-777/NFT callback reentrancy, approval residuals,
manipulable/stale oracle reads, flash-loan price manipulation, signature replay,
cross-chain endpoint/peer spoofing, first-deposit share inflation, forced ETH,
CREATE2 squatting, or asynchronous state races. Map these to actual Vyper call
sites and state transitions; do not report named patterns without a traced,
profitable or materially harmful path.

## Sources to re-check when updating this skill

- Vyper release notes: <https://docs.vyperlang.org/en/stable/release-notes.html>
- Vyper security advisories: <https://github.com/vyperlang/vyper/security/advisories>
- External interfaces: <https://docs.vyperlang.org/en/stable/interfaces.html>
- Control structures and nonreentrancy: <https://docs.vyperlang.org/en/stable/control-structures.html>
- Built-ins: <https://docs.vyperlang.org/en/stable/built-in-functions.html>
- Modules: <https://docs.vyperlang.org/en/stable/using-modules.html>
