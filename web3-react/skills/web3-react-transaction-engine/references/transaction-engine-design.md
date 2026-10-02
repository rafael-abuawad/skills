# Reusable Transaction Engine: Interface Exploration

This exploration turns the transaction patterns observed in Uniswap Interface into a reusable module rather than a copied Redux/Saga subsystem.

## Requirements

Callers need to run a sequence such as `approve → sign permit → execute`, preserve a user-visible activity record after the modal unmounts, deduplicate accidental duplicate submissions, wait for actual confirmation where required, support classic transaction hashes and future operation/batch IDs, and trigger narrowly scoped cache reconciliation. The design must not persist sensitive signing payloads, raw signatures, or arbitrary calldata.

The module's callers are feature flows, a root application watcher, UI views/toasts, and tests. The module hides transition validity, durable record format, ordering rules, operation-ID resolution, and terminal-state semantics. Wallet/chain libraries remain adapters, not part of the module interface.

## Design A — A React `useTransactionFlow` Hook

```ts
const flow = useTransactionFlow({
  steps: [approvalStep, permitStep, depositStep],
  onConfirmed,
})
await flow.submit()
```

It is initially attractive: a feature gets one hook and status flags. The hook would hide Wagmi mutations, effects, and local status.

**Why it loses:** it couples execution to a mounted React tree. Navigating away loses the transaction watcher or forces the hook to grow persistence, subscriptions, background effects, and dozens of callback options. Its interface becomes shallow because all wallet, cache, rendering, and storage decisions leak through options. It is suitable only for a one-shot, non-durable form.

## Design B — A Fully Generic Workflow/DAG Runtime

```ts
engine.run({ nodes, edges, retryPolicy, compensation, persistence, renderers, transports })
```

This could model parallel, cross-chain, conditional, and compensating workflows.

**Why it loses as the default:** the caller has to learn graph semantics, generic failure/retry policy, persistence schema, and scheduling behavior before sending an ERC-20 approval. The wide interface increases misuse risk. It also gives a false sense that an arbitrary cross-chain protocol can safely be “generic.” A DAG executor may be warranted later for a bridge/intent product, but it should not be the baseline dapp module.

## Design C — Durable Ledger + Ordered Runner (**selected**)

```ts
const record = createTransactionRecord({ action, account, chainId, steps, ... })
store.save(record)

record = reduceTransaction(record, { type: 'step-requested', stepId, at: Date.now() })
store.save(record)
// Adapter opens wallet; runner converts outcome into the next event.
```

The selected design has two tightly focused modules behind separate seams:

1. **Transaction ledger** — a framework-independent, pure state machine that owns serializable records, valid phase transitions, ordered-step constraints, transaction/user-operation/batch references, and terminal semantics.
2. **Ordered runner** — an app-specific adapter that reads the current record, runs the next step through Wagmi/Viem (or a smart-account adapter), persists reducer events before/after side effects, and hands submitted references to a root-level watcher.

The **external interface** is deliberately small: create a record, reduce an event, inspect the current step/phase, and let a persistence adapter save/subscribe. A caller supplies semantic step definitions and a `dedupeKey`; the module hides lifecycle mechanics.

### What it hides

- A dependent step cannot request a wallet action until each predecessor confirms.
- Broadcast, confirmation, revert, wallet rejection, and local/RPC failure are distinct.
- A batch/user-operation ID can later resolve to its on-chain transaction hash without changing feature-owned identity.
- Persisted activity never contains a signature, private payload, raw typed data, full arbitrary calldata, or a closure needed to resume a flow.
- Terminal transaction attempts stay immutable in history. Retrying creates a new attempt, avoiding a misleading “rejected then confirmed” record.

### Why it is deep

Feature callers learn a small event vocabulary and provide semantic steps. Tests can exercise all ordering and terminal behavior through one pure reducer. The runner, watcher, cache effects, storage, Wagmi calls, and UI become interchangeable adapters behind internal seams. Deleting this module would reintroduce ordering, persistence, status, and error complexity into every dapp feature.

## Scope Boundary

The template is intentionally not a full execution SDK:

- It does **not** build calldata, parse quotes, choose approval policy, or decide confirmations. Those are domain preparation responsibilities.
- It does **not** expose a generic cross-chain workflow graph. Cross-chain features should represent source and destination actions explicitly until their requirements justify a dedicated module.
- It does **not** call a wallet. The runner adapter validates/simulates immediately before it emits `step-requested` and then maps Wagmi/Viem outcomes into reducer events.
- It does **not** automatically retry. An automatic retry could repeat an authorization or send a stale transaction; retry policy belongs to the feature and must be explicit.

## Reference Integration Shape

```text
feature prepare/validate
  └─ creates semantic ordered steps + dedupe key
       └─ ledger stores `ready` record
            └─ runner: simulate → requested → wallet → submitted
                 └─ root watcher: confirming → confirmed/reverted
                      └─ effect adapter invalidates scoped queries + emits safe analytics
```

The runner should persist `step-requested` before showing a wallet prompt, persist `step-submitted` immediately after receiving an ID/hash, and never make UI mounting a prerequisite for a confirmation watcher. The watcher must scope its public client by the record's `chainId`, not the currently selected wallet chain.

## Extracted Source Evidence

- `apps/web/src/state/sagas/transactions/utils.ts`: explicit signature/on-chain steps, interruption boundaries, confirmation wait, duplicate detection, batch-ID-to-hash resolution, and rejection filtering.
- `apps/web/src/state/transactions/adder.ts` and `hooks.tsx`: a durable record includes account, chain, semantic type info, timing, and pending status rather than only a local mutation result.
- `packages/uniswap/src/features/transactions/types/transactionDetails.ts`: classic hashes, 4337 user-operation hashes, EIP-5792 batch IDs, receipts, replacement/cancellation, and final versus temporary states must not be collapsed into one `isLoading` flag.
- `apps/web/src/features/transactions/TransactionWatcherProvider.tsx`: the watcher belongs above route/modal lifetime.
- `packages/wallet/src/features/transactions/executeTransaction/services/TransactionService/transactionService.ts`: transaction, synchronous submission, and user operation paths are related but distinct adapters.
