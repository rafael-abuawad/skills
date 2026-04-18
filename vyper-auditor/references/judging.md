# Finding Validation

Every finding passes four sequential gates. Fail any gate → **rejected** or **demoted** to lead. Later gates are not evaluated for failed findings.

## Gate 1 — Refutation

Construct the strongest argument that the finding is wrong. Find the guard, check, or constraint that kills the attack — quote the exact line and trace how it blocks the claimed step.

- Concrete refutation (specific guard blocks exact claimed step) → **REJECTED** (or **DEMOTE** if code smell remains)
- Speculative refutation ("probably wouldn't happen") → **clears**, continue

Vyper-specific guards to check:

- `@nonreentrant("...")` (≤0.3.x) or `@nonreentrant` (0.4+) on the entry point — but verify it covers ALL paths, not just one of two `@external` functions writing the same state
- `assert msg.sender == ...` inline guards or snekmate `ownable._check_owner()` / `access_control._check_role(...)`
- `default_return_value=convert(1, bytes32)` on `raw_call` — does the consumer of the returned value validate it independently?
- `convert(x, uintN)` reverts on overflow — if the result is then `unsafe_*`'d it loses the protection

## Gate 2 — Reachability

Prove the vulnerable state exists in a live deployment.

- Structurally impossible (enforced invariant prevents it) → **REJECTED**
- Requires privileged actions outside normal operation → **DEMOTE**
- Achievable through normal usage or common token behaviors (fee-on-transfer, rebasing, blacklisting, pausing) → **clears**, continue

## Gate 3 — Trigger

Prove an unprivileged actor executes the attack.

- Only trusted roles can trigger → **DEMOTE**
- Costs exceed extraction → **REJECTED**
- Unprivileged actor triggers profitably → **clears**, continue

## Gate 4 — Impact

Prove material harm to an identifiable victim.

- Self-harm only → **REJECTED**
- Dust-level, no compounding → **DEMOTE**
- Material loss to identifiable victim → **CONFIRMED**

## Confidence

Start at **100**, deduct: partial attack path **-20**, bounded non-compounding impact **-15**, requires specific (but achievable) state **-10**. Confidence ≥ 80 gets description + fix. Below 80 gets description only.

## Safe patterns (do not flag)

- Vyper >= 0.3 reverts on overflow/underflow by default — do not flag plain `+`/`-`/`*` as "missing SafeMath"
- `unsafe_*` used inside a provably-bounded loop counter (e.g., `for i in range(n): self.x = unsafe_add(self.x, 1)` with `n <= type-max`)
- Explicit `convert(x, smallerType)` (reverts on overflow)
- MINIMUM_LIQUIDITY burn on first deposit
- `@nonreentrant` correctly applied to all relevant entry points
- Two-step admin transfer (snekmate `Ownable2Step`)
- Consistent protocol-favoring rounding unless compounding or zero-rounding
- `raw_call(..., default_return_value=...)` where the called token is hardcoded immutable and known-compliant

## Lead promotion

Before finalizing leads, promote where warranted:

- **Cross-contract echo.** Same root cause confirmed as FINDING in one contract → promote in every contract where the identical pattern appears.
- **Multi-agent convergence.** 2+ agents flagged same area, lead was demoted (not rejected) → promote to FINDING at confidence 75.
- **Partial-path completion.** Only weakness is incomplete trace but path is reachable and unguarded → promote to FINDING at confidence 75, description only.

## Leads

High-signal trails for manual investigation. No confidence score, no fix — title, code smells, and what remains unverified.

## Do Not Report

Linter/compiler issues, gas micro-opts, naming, NatSpec. Admin privileges by design. Missing events. Centralization without exploit path. Bounded `for x in range(N)` loops where `N` is a small constant. Implausible preconditions (but fee-on-transfer, rebasing, blacklisting ARE plausible for contracts accepting arbitrary tokens).
