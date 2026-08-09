---
name: web3-react-transaction-engine
description: Designs and implements durable transaction orchestration for React dapps: ordered approval/signature/write steps, persistent transaction history, receipt and operation watchers, deduplication, replacements, batch/user-operation IDs, and cache reconciliation. Use when a transaction must survive modal closure, navigation, refresh, or multiple dependent steps.
---

# Web3 React Transaction Engine

Use this skill when a single `useWriteContract` result is no longer enough. Load `web3-react-transactions` for contract simulation/write details, `web3-react-onchain-data` for cache policy, and `web3-react-account-abstraction` for smart-account execution adapters.

The goal is a **deep module**: feature code describes a semantic action and its ordered steps; one engine owns durable lifecycle state, transition validity, watchers, and reconciliation. Do not copy Uniswap's Redux/Saga implementation into a normal dapp.

Read [the interface exploration](references/transaction-engine-design.md) before designing a new engine. The selected design is **durable ledger + ordered runner**, not a component-bound hook or a generic workflow/DAG framework.

A framework-independent starter is available at [templates/transaction-machine.ts](templates/transaction-machine.ts). Copy it into the app, test it as a pure module, then add app-specific storage, runner, watcher, and React adapters.

## Core Model

Separate four concerns at clear seams:

1. **Preparation (feature-owned):** validate current intent, choose exact approval/permit/call steps, construct a semantic `dedupeKey`, and determine confirmation requirements.
2. **Ledger (engine-owned):** persist a small redacted record, enforce legal state transitions, and expose the current ordered step. It has no React, Wagmi, or UI dependency.
3. **Runner (adapter):** performs just the current step using the installed wallet stack. It revalidates/simulates immediately before requesting the wallet, then turns outcomes into persisted ledger events.
4. **Watcher/effects (application-owned adapter):** observes pending transaction/user-op/batch references at the root of the app, applies terminal ledger events, invalidates scoped queries, creates notifications, and emits redacted telemetry.

```text
feature preparation
  → ledger: ready
  → runner: awaiting-wallet → submitted
  → root watcher: confirming → confirmed | reverted | failed
  → effects: scoped cache reconciliation + activity/notification
```

A React modal observes this record; it is not the record's owner. A route change, modal close, or app refresh must not erase a submitted action.

## Required States

At minimum distinguish these states—never collapse them into a boolean:

| State | Meaning |
| --- | --- |
| `ready` | A valid prepared next step exists; no wallet prompt is open. |
| `awaiting-wallet` | Wallet prompt requested; user has not accepted/rejected. |
| `submitted` | A hash/user-operation hash/batch ID was returned; inclusion is unknown. |
| `confirming` | A watcher is resolving the submitted reference. |
| `confirmed` | Required receipt/finality condition was satisfied. |
| `rejected` | User rejected a wallet prompt or required chain switch. This is cancellation, not an app failure. |
| `reverted` | An on-chain operation landed unsuccessfully. |
| `failed` | Validation, RPC, timeout, or invariant failure prevented success. |

For flows with multiple steps, a later step can start only after every required predecessor is `confirmed`. A permit signature may complete directly from `awaiting-wallet`; an approval must normally obtain a successful receipt before the action step begins.

## Durable Record Rules

Persist a versioned, JSON-safe record scoped by:

- immutable record ID and optional feature-owned `dedupeKey`;
- account, chain ID, semantic action/type, creation/update time;
- ordered semantic steps with phase, safe label, and a reference if submitted;
- transaction hash, user-operation hash, or EIP-5792 batch ID as distinct reference kinds;
- a minimal receipt/finality summary and a categorized, safe error summary.

**Never persist** private keys, signatures, raw typed data, session credentials, arbitrary backend responses, complete calldata by default, or React closures. Keep the prepared executable request in memory or reconstruct it from current, validated domain state. After a refresh, the engine can safely watch submitted references; any unsigned next step should be reconstructed and revalidated rather than blindly resumed.

Generate `dedupeKey` from stable business identity (for example `approve:<chain>:<owner>:<token>:<spender>:<amount-policy>`). Do not dedupe with `JSON.stringify` of a mutable request. Before opening a wallet prompt, check for a matching pending/recent record; either attach to its watcher or clearly require a new attempt.

## Runner Contract

A runner should be a narrow adapter, conceptually:

```ts
interface TransactionRunner {
  runNext(recordId: string): Promise<void>
}
```

Its internal algorithm is:

1. Load the record; reject terminal records and resolve the one next non-confirmed step.
2. Check account, target chain, supported deployment/capability, current inputs, deadline/quote version, balances/allowance/nonces, and duplicate policy.
3. Simulate/estimate with the actual account, chain, value, and current call.
4. Persist `step-requested` **before** opening a signature or wallet prompt.
5. Call the appropriate adapter: typed-data sign, `writeContract`, `sendTransaction`, `wallet_sendCalls`, or user-op submission.
6. On user rejection, persist `step-rejected` and return without alarming telemetry.
7. On a returned reference, persist `step-submitted` immediately, register it with the root watcher, and return control to the UI.
8. The watcher persists `confirming`, then `confirmed`, `reverted`, or `failed`; it triggers post-confirmation effects exactly once.

Do not let a runner automatically repeat a rejected signature, a write, or a stale quote. Explicit user retry should create a fresh attempt or deliberately re-enter a new prepared flow.

## References Are Not Interchangeable

```ts
// Do not normalize these into one fake transaction hash.
type Reference =
  | { kind: 'transaction'; chainId: number; hash: `0x${string}` }
  | { kind: 'user-operation'; chainId: number; userOpHash: `0x${string}`; transactionHash?: `0x${string}` }
  | { kind: 'wallet-call'; chainId: number; batchId: string; transactionHash?: `0x${string}` }
```

- A normal transaction hash is observed through the chain's public client.
- A 4337 user-op hash needs bundler/entry-point-aware resolution to its on-chain hash and can expire without a receipt.
- An EIP-5792 batch ID might resolve through `wallet_getCallsStatus`, then later yield an on-chain hash. Do not put a batch ID in an explorer URL.
- A replacement/speed-up/cancellation needs a link from the original record to the replacement reference and an explicit final state for the original.

## Root Watcher and Reconciliation

Mount one `TransactionCenter`/watcher at application-provider level. It should:

- select every persisted, non-terminal record owned by the active/relevant account;
- group work by `chainId`, use the app public client, bound concurrency, and avoid a poller per rendered row;
- apply receipt finality/confirmation policy appropriate to the action;
- resolve user-op/batch status using their own adapters;
- tolerate temporary RPC/indexer failures as retryable `confirming`, not as an invented revert;
- update ledger first, then execute idempotent effects: invalidate exact balance/allowance/position/activity queries, show notification, and track a redacted semantic event;
- reconcile after confirmation even when an optimistic cache mutation was applied.

Keep an idempotency marker for finalization effects or make each effect idempotent. A watcher can run more than once after refresh/network reconnect; it must not send duplicate notifications or write stale cache values.

## Feature Integration Example

```ts
const record = createTransactionRecord({
  id: crypto.randomUUID(),
  action: 'deposit-vault',
  account,
  chainId,
  dedupeKey: `vault-deposit:${chainId}:${account}:${vault}:${assets}`,
  steps: [
    { id: 'approve', label: 'Approve token', kind: 'transaction' },
    { id: 'deposit', label: 'Deposit', kind: 'transaction' },
  ],
  metadata: { vault, assetSymbol: 'USDC' },
  at: Date.now(),
})

await ledger.save(record)
await runner.runNext(record.id)
// UI subscribes to record.steps; watcher later starts `deposit` only after approve confirms.
```

The feature owns construction of the actual approval/deposit request and the post-confirmation query keys. The engine does not infer protocol semantics from arbitrary calldata.

## Testing the Module

Test the ledger reducer without React or a chain:

- empty or duplicate step definitions reject;
- later step cannot start before predecessor confirmation;
- signature can resolve directly after wallet acceptance;
- broadcast and confirmation are different phases;
- rejection/revert/failure are terminal and cannot silently become success;
- a user-op/batch reference can resolve to a transaction hash;
- serialized records contain no secret/signature/request payload.

Test adapters separately with mocked wallet/public clients. Then E2E test the full path: prepare → wallet acceptance → stored hash/reference → modal unmount/route change → receipt/finality → scoped cache refresh. Include rejection, RPC timeout, replacement, and failure/revert cases that apply to the feature.

## Source-Derived Patterns

- `apps/web/src/state/sagas/transactions/utils.ts`: ordered signature/on-chain steps, duplicate detection, interrupt handling, receipt wait, approval-modification checks, and batch ID resolution.
- `apps/web/src/state/transactions/adder.ts` and `hooks.tsx`: record transactions with owner/account, chain, semantic type, timing, and pending state—not just a component mutation result.
- `packages/uniswap/src/features/transactions/types/transactionDetails.ts`: distinguish hashes, user-op hashes, batch IDs, replacements/cancellations, and final/temporary states.
- `apps/web/src/features/transactions/TransactionWatcherProvider.tsx`: watcher lifetime exceeds feature UI lifetime.
- `packages/wallet/src/features/transactions/executeTransaction/services/TransactionService/transactionService.ts`: transaction and user-op execution deserve separate adapters behind one semantic execution layer.
