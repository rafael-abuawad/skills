# Senior Vyper Auditor's Mindset

Known-pattern scans find obvious bugs. High-value findings come from how an auditor
reasons when code looks ordinary, not just from knowing a longer vulnerability
checklist. Use these tools continuously alongside the Vyper-language reference.

A finding is not real until you have traced it with concrete values through Vyper's
actual decorators, module boundaries, external calls, and storage effects. You are
an attacker, not a defender: after finding a flaw, deepen the attack rather than
explaining it away.

## 1. Feynman test — always first

When opening a contract, module, or function, explain it in plain language before
reasoning about it. Do not hide behind Vyper terms such as `extcall`, `uses:`, or
`@nonreentrant`.

`_collect_fee` is not explained by “it does an extcall.” Explain: “it takes the
user's payment, keeps the protocol fee, and sends the rest to the recipient.” Then
ask: what happens for native ETH, a fee-on-transfer token, an ERC-20 returning
false, a token with no return bytes, a reentrant receiver, or an imported module
whose initializer did not run? Wherever the explanation becomes fuzzy, name the
assumption. That is the attack surface.

## 2. Socratic questioning

For each security-relevant line, ask why it exists, what it assumes, and who can
make the assumption false. Do not accept the function name or a comment as proof.
Drill until the implicit belief is exposed.

Example: `if asset != NATIVE: assert extcall IERC20(asset).transferFrom(...)`.

- Why skip the call for native ETH? Native value presumably arrived in `msg.value`.
- Where is `msg.value == amount` enforced on that branch?
- Does the native branch deduct the same fee and update the same state as the token
  branch?

If there is no answer, the security property is missing.

## 3. Inversion

After understanding the intended path, run it backward as an attacker. For every
check, ask what value, caller, callback, imported-module state, or transaction
ordering slips through it. For every external call, ask what changes before control
returns. For every module export, ask whether the host exposes it in a context its
author did not anticipate.

A clean-looking path deserves the strongest inversion: a false-returning token,
empty return data, a reentrant callback, a stale oracle, zero/one/max input, an
uninitialized child, or a multi-transaction interleaving.

## When to apply the tools

- Opening any function, module, or contract: **Feynman** first.
- A line's purpose or precondition is unclear: **Socratic**.
- A path, guard, or check appears sufficient: **Inversion**.
- You reach a candidate finding: amplify it — lower setup cost, find additional
  victims, chain its effects, and prove the actual impact.

Trust discomfort, but do not report it as certainty. A complete proof becomes a
FINDING; an unverified but concrete trail becomes a LEAD.
