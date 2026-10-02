---
name: web3-react-defi-execution
description: Builds safe DeFi execution flows in React for swaps, liquidity, vault deposits/withdrawals, bridges, and routed transactions. Use for quote freshness, slippage, price impact, routing, trade warnings, approval/permit selection, executable calldata validation, multi-step execution plans, cross-chain progress, or transaction review UX.
---

# Web3 React DeFi Execution

Use this skill for economic execution flows, not generic reads. Load `web3-react-transactions` for wallet/receipt mechanics, `web3-react-dapp-security` for risk policy, and `web3-react-transaction-engine` when execution has durable multiple steps.

Do not copy a DEX aggregator's routing implementation blindly. Extract the invariant pattern: separate discovery from executable intent, validate the executable result, expose economic risk, and turn it into ordered transaction steps.

## Separate the Four Artifacts

A correct DeFi flow has distinct artifacts:

1. **Form intent** — user-selected assets, exact input/output mode, amount string, recipient, settings. Mutable and not executable.
2. **Indicative quote** — useful for fast display. It may be stale, partial, or non-executable; label it accordingly.
3. **Executable quote/instructions** — chain/account/amount/settings-bound route with expiry/request ID and exact calldata or signed-order preparation requirements.
4. **Accepted execution plan** — immutable snapshot reviewed by the user. It contains validated semantic effects and ordered steps, and must be invalidated if any material condition changes.

Never let a screen sign an indicative quote. Never keep using an executable quote after account, chain, token, amount, recipient, slippage/deadline, capability, or expiry changed.

## Quote Query Design

Use a canonical request builder and query key. It should include:

- input/output chain and normalized token/native identifiers;
- exact-side, parsed raw amount, recipient, account/sender when route/simulation depends on it;
- user settings: slippage, deadline, route/protocol preference, gas/sponsorship choice;
- feature/version/config flags that change executable result.

Debounce form display work, cancel obsolete requests, and preserve the last valid quote only for clearly marked display—not submission. Use an explicit quote ID/digest and expiration. A new quote must supersede the old review plan; do not compare a displayed amount alone.

At review/submit, refetch or validate quote freshness and resimulate the final executable call when the protocol supports it. If price moved beyond the accepted protection, return to review with a clear “quote changed” decision rather than silently updating terms.

## Economic Correctness

Maintain raw amounts as `bigint` and derive bounds from the execution type:

| Mode | User protection |
| --- | --- |
| Exact input | `minimumAmountOut` after slippage, fees, and known transfer behavior. |
| Exact output | `maximumAmountIn` after slippage, fees, and known transfer behavior. |
| Deposit/mint | minimum shares/minted position or maximum assets, as protocol supports. |
| Withdraw/redeem | minimum assets/outputs or maximum shares burned, as protocol supports. |
| Bridge/chained route | each step's bound plus a clearly communicated aggregate/compound risk. |

Do not calculate protected bounds with JS `number`. Preserve quote-provided integer bounds where authoritative; otherwise use exact rational/BigInt arithmetic with tested rounding direction.

For chained routes, communicate that independent step slippages compound:

```ts
// Percent form: 1 - Π(1 - stepSlippage / 100)
const compound = 1 - slippages.reduce((factor, value) => factor * (1 - value / 100), 1)
```

A source-chain receipt is not destination-chain completion. Show source submitted/confirmed, relay/intent status, destination submitted/confirmed, and claimability as distinct stages.

## Warning and Review Policy

Build a pure, ordered decision function for the review CTA. Typical precedence:

1. form incomplete/invalid or unsupported chain/platform;
2. wallet connect / view-only / wrong-chain action;
3. hard policy block (token, address, compliance, expired executable quote);
4. mandatory safety acknowledgement (token risk, bridged asset, contract recipient);
5. economic warnings (price difference/impact, slippage, fee-on-transfer, low native gas balance, unusual route);
6. review/execution.

Each acknowledgement must bind to the accepted quote/plan digest. Reset it when a material input or quote changes. Do not conflate “warning dismissed” with “safe forever.”

The review must disclose, where applicable: input/output and protected bounds, token fee, protocol/aggregator fees, network fee and payer, slippage/deadline, recipient, route/intermediate assets, source/destination chains, bridge delay, approval spender, permit method, sponsorship conditions, and all transaction steps.

## Validate Executable Instructions

A backend/routing service may build efficient calldata but it is still external input. Validate before creating steps:

- expected quote/request ID, chain, sender/account, deadline, and recipient;
- deployment/target allowlist, data/value schema, token addresses, raw amounts, and route semantics;
- mutually exclusive execution representations: EOA transaction(s), `wallet_sendCalls`, typed-data order, or unsigned user operation;
- gas fee/sponsorship presence and consistency; sponsorship advertised but not delivered is a blocking mismatch;
- all approval/revocation/permit instructions against the selected token/spender/amount policy;
- simulation/preflight against the final user/account context.

If the external response is incomplete or contradictory, stop. Do not infer missing executable pieces from stale form data.

## Generate Steps as Pure Domain Data

Convert a validated plan into pure, ordered semantic steps before the wallet opens:

```ts
type ExecutionStep =
  | { kind: 'revoke'; token: Address; spender: Address; request: Request }
  | { kind: 'approve'; token: Address; spender: Address; request: Request }
  | { kind: 'permit-signature'; typedData: TypedData }
  | { kind: 'permit-transaction'; request: Request }
  | { kind: 'execute'; request: Request | WalletCall | UserOperation }
```

Ordering is protocol-specific but must be deterministic and tested. A classic flow might be reset → approve → permit → execute; a typed-data intent may be approve → sign order; an atomic wallet batch may have one reviewed batch step but must still enumerate its constituent semantic effects. Advance dependent steps only after the required prior confirmation.

Freeze the accepted plan during execution. If the user cancels/rejects, keep or regenerate only an unexpired plan; if price/quote state changed, require fresh review.

## DeFi Execution Test Matrix

Unit test request building, bound rounding, quote keys, staleness/digest invalidation, warning precedence, executable validation, and step ordering. Fork/Anvil E2E test:

- exact-in/out postcondition and protected min/max bounds;
- price/quote changes requiring new acceptance;
- high price difference, fee-on-transfer, token risk, bridged-asset, and low gas warnings;
- approval, zero-reset, permit, and action order;
- executable payload mismatch/expired route rejection;
- multi-step interruption/retry and source-vs-destination bridge progress.

## Source-Derived Patterns

- `packages/uniswap/src/features/transactions/swap/services/prepareSwapService.ts`: convert review entry into one ordered, pure decision/action path; reset temporary warning state after handling.
- `packages/uniswap/src/features/transactions/swap/types/validateSwapTxContext.ts`: validate each execution representation and block promised-but-undelivered gas sponsorship rather than silently degrading terms.
- `packages/uniswap/src/features/transactions/swap/utils/generateSwapTransactionSteps.ts`: derive protocol-specific approval/revocation/permit/execution steps as testable domain data before execution.
- `packages/uniswap/src/features/transactions/swap/plan/slippage.ts`: multi-step risk compounds; do not present only an arbitrary individual-step tolerance.
- `packages/uniswap/src/features/transactions/swap/services/warningService.ts`: warnings are explicit, scoped product state rather than generic errors or permanent global dismissals.
- `apps/web/src/pages/Swap/Swap/Swap.anvil.e2e.test.ts`: exercise quote configuration, permit behavior, warning acknowledgement, actual wallet flow, and on-chain postconditions together.
