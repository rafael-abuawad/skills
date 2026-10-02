---
name: web3-react-account-abstraction
description: Adds smart-account and advanced wallet execution safely to React dapps: EIP-5792 wallet_sendCalls batches, ERC-4337 user operations, EIP-7702 delegations, paymasters, passkeys, wallet capability negotiation, operation status tracking, and EOA fallbacks. Use when implementing account abstraction, batched calls, gas sponsorship, embedded wallets, or delegated execution.
---

# Web3 React Account Abstraction

Advanced wallet execution is additive. First make the standard EOA `simulate → sign → send → receipt` path correct with `web3-react-transactions`; then add capability-gated adapters. Do not force smart-account abstractions into an application that only needs normal transactions.

## Capability First, Feature Second

Capability is a property of **connector + account + chain + current wallet state**, not of a wallet brand.

1. Request capability data with a timeout.
2. Validate it as untrusted external data; normalize chain identifiers before lookup.
3. Store an account/connector/chain-scoped snapshot with `unknown`, `supported`, `unsupported`, or `unavailable` status.
4. Re-query after account, connector, or chain changes.
5. Require both wallet support and an app/product allowlist before an advanced path.
6. Choose one of three results per feature:
   - use the enhanced path;
   - fall back to a documented sequential EOA path;
   - block the operation when atomicity or sponsorship is a hard invariant.

Never silently turn an `atomicRequired` batch into several independent transactions. Never promise sponsored gas merely because a quote offered it; record sponsorship only if the final executed operation contains/uses the paymaster path.

## EIP-5792 `wallet_sendCalls`

Before calling `wallet_sendCalls`:

- validate `chainId` hex encoding and ensure it is the active/required chain;
- ensure requested `from` equals the connected account after normalization;
- validate every call's target, calldata, value, and feature allowlist just as for a normal transaction;
- validate atomicity and paymaster capability against the wallet snapshot;
- render all calls/aggregate asset effects in review UI; batching must not hide an approval or delegation;
- create a durable reference with `{ kind: 'wallet-call', batchId, chainId }` immediately on return.

`batchId` is not necessarily an on-chain transaction hash. Watch it through `wallet_getCallsStatus` or a wallet-specific status adapter. When it resolves, attach the actual hash/receipt to the same record; only then create explorer links or treat it as on-chain confirmation.

## ERC-4337 User Operations

Treat a UserOperation as a distinct execution adapter with distinct identifiers and failure modes:

```text
validated intent/calls
 → optional paymaster preparation + bundler simulation
 → account/user-op signature
 → bundler submission returns userOpHash
 → operation watcher resolves inclusion/revert/expiry and transaction hash
 → normal receipt/finality reconciliation
```

- Validate entry point, chain, sender, call data, nonce, gas fields, paymaster endpoint/context, and expiry before signing.
- A `userOpHash` is not a transaction hash. Persist it separately and resolve it through a bundler/indexer/entry-point-aware watcher.
- Distinguish temporary status lookup/outage from a terminal rejection, failed simulation, expired operation, and reverted included transaction.
- Do not put sponsor contexts, session credentials, signatures, or raw operation payloads in client persistence/telemetry.
- Consider paymaster refusal a normal actionable branch; do not silently make users pay after advertising sponsorship unless the product explicitly asks them to accept the change.

## EIP-7702 Delegation

EIP-7702 changes the authority model of an EOA. Treat delegation authorization as a high-risk, chain-bound signature:

- require audited/allowlisted delegation implementation addresses;
- show the delegation target and consequence distinctly from the ordinary action;
- use the exact chain ID and the correct pending EOA nonce; EOA nonce and UserOp nonce are different;
- validate encoding/signature fields rigorously, including byte width/padding and recovered signer;
- handle races between pending-nonce read and submission by re-preparing rather than guessing;
- record whether the executed operation actually includes delegation, but do not persist authorization signatures.

Do not use EIP-7702 merely as a transport optimization. Require explicit product and audit rationale.

## Embedded Wallets and Passkeys

Embedded-wallet/passkey flows add device/session/recovery attack surfaces outside ordinary dapp connection:

- isolate key material and recovery flows from React/UI state; never log or persist recovery secrets client-side beyond the wallet provider's reviewed design;
- make provider/session initialization explicit and bounded by timeouts;
- account for passkey/browser support, cancellation, recovery, and cross-device state as product flows, not generic connector errors;
- separate wallet authentication from authorization to execute a particular call;
- test first-use delegation, already-delegated accounts, restored sessions, and user rejection independently.

For most dapps, consume a well-reviewed embedded wallet provider rather than implementing signer, passkey, recovery, encryption, bundler, and paymaster infrastructure from scratch.

## Transaction Engine Integration

Use `web3-react-transaction-engine` references:

```ts
type AdvancedReference =
  | { kind: 'wallet-call'; batchId: string; chainId: number; transactionHash?: `0x${string}` }
  | { kind: 'user-operation'; userOpHash: `0x${string}`; chainId: number; transactionHash?: `0x${string}` }
```

The runner persists an advanced reference after submission. A root-level operation watcher resolves it. The feature should not guess its result from a returned ID or close the flow as successful before terminal status.

## Tests

Test at three levels:

- **Pure validation:** malformed capabilities, chain IDs, `from`, calls, atomic requirements, paymaster context, nonce/signature/delegation serialization.
- **Adapter tests:** capability timeout/unavailable, EOA fallback, wallet batch response, user-op hash resolution, bundler temporary error, terminal expiration, paymaster rejection.
- **Fork/Anvil or dedicated integration:** actual batch atomicity, user-op/delegation behavior where infrastructure is available, and state reconciliation after refresh/unmount.

## Source-Derived Patterns

- `apps/web/src/state/walletCapabilities/lib/handleGetCapabilities.ts` and `ensureValidatedCapabilities.ts`: time-bound capability query, normalization, validation, conservative unsupported fallback.
- `packages/embedded-wallet/src/connection/sendCalls.ts`: validate EIP-5792 chain/from before signing; branch deliberately among sponsored 4337, delegated multicall, and normal transaction paths.
- `packages/embedded-wallet/src/connection/getCallsStatus.ts`: batch/user-op identifiers need a status resolver that can map them to a real transaction hash or terminal expiry.
- `packages/wallet/src/features/transactions/executeTransaction/services/TransactionService/transactionService.ts`: EOA transactions and user operations are separate typed execution paths.
- `packages/wallet/src/features/transactions/executeTransaction/eip7702Utils.ts`: EIP-7702 authorization must bind exact chain/nonce, verify signer, and handle strict serialized signature encoding.
