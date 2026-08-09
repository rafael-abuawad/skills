# Finding Validation

Every candidate passes four gates in order. Fail a gate: reject it or demote it to
a lead, then do not evaluate later gates. These gates test whether the claimed
attack actually reaches material harm — not whether the code appears unusual.

Before Gate 1, apply the compiler-context rule from `vyper-language.md`: a
compiler-specific claim requires a deployed or reproducibly configured affected
Vyper version. Unknown version means a lead, not a finding.

## Gate 1 — Attack execution

Trace the claimed path from the caller to harm. Read every `assert`, branch,
decorator, module boundary, `exports:` entry, external-call result check, and
constraint on that exact path.

- A concrete source-level interruption blocks the claimed exploit before harm
  (quote it and explain the trace) → **REJECTED**, or **DEMOTED** if a distinct
  code smell remains.
- An assumed interruption (“the token is probably standard”, “the owner would not
  do that”, “the UI prevents it”) → clears this gate.

Vyper-specific checks:

- For `<0.4.0`, map every `@nonreentrant("key")` involved; a different key is not
  a guard. For `>=0.4.0`, map global `@nonreentrant`, and for `>=0.4.2` determine
  whether `# pragma nonreentrancy on` covers the **current file** and whether
  `@reentrant`/`reentrant(T)` opts out. Imported module files have independent
  settings.
- Verify inline authority checks, snekmate module checks, module initialization,
  and exported entry points on the actual route.
- For `extcall`, verify a boolean transfer result is asserted. If
  `default_return_value=True` is used, verify it is an intentional no-return-token
  policy, code-existence is not skipped without reason, and the defaulted result is
  asserted before accounting.
- For `raw_call`, verify the claimed route handles `revert_on_failure=False`
  success flags, response length, decode validity, and delegatecall storage
  context. `default_return_value` is not a raw-call option.
- For a claimed arithmetic wrap, distinguish ordinary checked arithmetic,
  bounds-checked `convert`, and `unsafe_*`/`pow_mod256`. A normal checked operation
  stops extraction, though a reachable critical revert may be a separate DoS lead.

## Gate 2 — Reachability

Prove that the vulnerable state can exist in a deployed system.

- An enforced invariant, compiler version outside the affected range, or impossible
  module/factory state → **REJECTED**.
- It requires a privileged action outside normal operation → **DEMOTED**, subject
  to the admin-action rule below.
- It follows from normal use or realistic asset behavior — fee-on-transfer,
  rebase, blacklist/pause, false/no-return tokens, ERC-777/NFT callbacks, stale or
  manipulable oracles, and cross-chain delay — clears this gate.

## Gate 3 — Trigger

Prove that an unprivileged actor can execute the attack and, where relevant, that
the economics are viable.

- Only a trusted role can trigger it → **DEMOTED**.
- Cost exceeds attainable extraction and there is no material griefing/lock impact
  → **REJECTED**.
- An unprivileged actor triggers it profitably or can materially lock/impair others
  → clears this gate.

### Admin-action findings

This rule applies only when harm depends on an admin acting maliciously or against
documented intent. Reject it — do not emit a lead — unless the finding names a
concrete unprivileged amplifier:

- **race:** an admin update creates a window a user can exploit;
- **retroactive sweep:** an update rewrites a pending user value;
- **asymmetric formula:** an admin-controlled value feeds a formula a user can
  exploit; or
- **access gap:** the authority/initialization mechanism itself is broken.

With an amplifier, judge the unprivileged path normally. This rule does not excuse
missing access control exploitable by an unprivileged caller.

## Gate 4 — Impact

Prove material harm to an identifiable victim or protocol property.

- Self-harm only → **REJECTED**.
- Dust-level, bounded, non-compounding harm → **DEMOTED**.
- Material loss, fund lock, insolvency, unauthorized control, or sustained
  protocol-wide liveness loss → **CONFIRMED**.

## Confidence

Start at **100**. Deduct:

- partial attack path: **-20**;
- bounded, non-compounding impact: **-15**;
- specific but achievable state: **-10**;
- compiler/deployment configuration not directly verified: **-20** (and prefer a
  lead when it is the sole proof).

Confidence **≥80** gets a description and a verified fix. Lower-confidence findings
get a description only. Never use a confidence score to conceal a missing exploit
step.

## Safe patterns — do not flag by themselves

- Ordinary Vyper arithmetic that reverts on overflow/underflow.
- Bounds-checked `convert(x, smaller_type)`.
- `unsafe_*` used only in a provably bounded operation where the full range proves
  no wrap.
- Correctly applied global nonreentrancy across all relevant current-file entry
  points, after checking module/file boundaries and read-only paths.
- An asserted interface-call result with a deliberate `default_return_value=True`
  policy for a known no-return token, without unsafe `skip_contract_check`.
- A `raw_call` to a hardcoded, immutable, known-compliant target whose success and
  expected response are fully validated.
- Minimum-liquidity protection against first-deposit inflation.
- Two-step administrator transfer, consistent protocol-favouring rounding that
  cannot compound, a small compile-time loop bound, and an intended administrative
  capability without an unprivileged amplifier.

## Lead promotion

Before final output, promote a lead when warranted:

- **Cross-contract echo:** the identical root cause is confirmed as a finding in
  one contract and appears in another reachable contract.
- **Multi-agent convergence:** two or more agents independently demoted (not
  rejected) the same issue; promote at confidence 75.
- **Partial-path completion:** the sole missing link has been completed from source
  and the route is reachable and unguarded; promote at confidence 75.

## Leads

A lead is a high-signal manual-investigation trail. It has no confidence score or
fix: include title, contract/function, code smell, the precise missing fact, and
what must be checked next.

## Do not report

Do not report linter/compiler warnings without a proven affected compiler and
material exploit, gas micro-optimizations, naming/NatSpec issues, missing events,
centralization without an exploit path, expected admin authority, or implausible
preconditions. Do not dismiss realistic arbitrary-token behavior — fee-on-transfer,
rebasing, blacklist/pause, false/no-return values, callback tokens, and stale
oracles are plausible unless the code restricts them.
