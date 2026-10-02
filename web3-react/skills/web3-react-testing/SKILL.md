---
name: web3-react-testing
description: Tests production EVM React dapps with deterministic unit, integration, and Anvil/fork E2E coverage. Use for contract interaction tests, wallet rejection, receipts/reverts, approvals/permits, transaction lifecycle, Playwright wallet flows, RPC mocks, fork setup, snapshots, or testing smart-account and DeFi execution paths.
---

# Web3 React Testing

A dapp test suite must validate both UI behavior and actual chain state. A mocked `writeContract` proving that a button called a function is not evidence that the wallet flow, calldata, allowance, receipt handling, or cache reconciliation works.

Use `web3-react-transactions` and `web3-react-transaction-engine` to define the lifecycle matrix first. This skill turns it into reliable tests.

## Test at Three Layers

### 1. Pure unit tests — fastest, most exhaustive

Keep these inputs/outputs dependency-free:

- address, amount, ABI/calldata, deadline, quote, deployment, and remote-payload validation;
- query-key and cache-predicate generation;
- token/recipient/risk severity classification;
- transaction engine reducer transitions, step ordering, error normalization, and dedupe key creation;
- approval/permit choice, reset-to-zero rules, slippage arithmetic, price/quote staleness, route selection;
- capability normalization and fallback decision.

Use fixed timestamps, chain IDs, addresses, `bigint` amounts, and fixtures. Assert semantic values, not implementation-specific hook calls.

### 2. Integration tests — adapters and React state

Mock the smallest external seam: public client, connector/wallet client, risk API, quote API, storage, or operation-status adapter. Verify:

- loading/disabled/error/unsupported/wrong-chain/rejection states;
- a simulation/write adapter passes exact chain/account/value/args;
- a returned hash becomes a durable pending record;
- user rejection is cancellation, not error telemetry;
- watcher terminal events invoke narrow cache invalidation once;
- account/chain switch cannot render or execute stale state;
- persisted record/query migrations are handled or safely discarded.

Do not mock the module under test and then assert its own internals. Test behavior through its interface.

### 3. Fork/Anvil E2E — final proof

Use a pinned fork or deterministic local deployment to assert actual outcomes:

```text
set known balances/allowances/state
 → navigate through the real UI
 → connect controlled wallet / choose chain
 → accept or reject wallet prompts
 → wait for visible pending/confirmed state
 → assert post-receipt balances, allowance, storage, event, or receipt on chain
```

Stub only remote systems that do not belong in a deterministic chain test—quote, indexer, risk, analytics, session services. Keep the contract write, wallet interaction, transaction status, and post-state assertion real where possible.

## Deterministic Anvil/Fork Discipline

A fork at the chain tip is not deterministic. Build a harness with:

1. **Pinned fork block** and explicitly recorded source/chain.
2. **Known test wallet** with controlled funding and a minimal allowlisted set of contract-state helpers.
3. **Per-test snapshot/revert** isolation. `evm_revert` consumes snapshots—check its returned boolean and take a fresh snapshot for every test.
4. **Recovery only at test boundaries.** Never restart/reset Anvil during a test because it invalidates all live snapshot IDs.
5. **Clock synchronization** when frontend/quote deadlines use wall time but the pinned fork is historical.
6. **Fee re-anchoring** at test boundaries when node configuration such as next-block base fee survives snapshot reverts.
7. **A real postcondition**: an output balance/event/receipt/storage assertion, not merely a success toast.

Do not expose a universal `setStorageAt` escape hatch to feature tests. Provide reviewed helpers for known tokens/contracts and a well-tested probing helper when storage layout manipulation is unavoidable.

## Test Wallet and Wallet UX

Use a controllable connector/provider for E2E paths. Cover both acceptance and `4001`-style rejection. Ensure the test framework can drive or simulate:

- initial connect, reconnect, disconnect, account change, and correct/wrong chain;
- signature rejection, transaction rejection, network-switch rejection;
- pending transaction while modal/route unmounts, then watcher-driven final state;
- permit signature then consuming transaction;
- reset-to-zero approval sequences for nonstandard ERC-20s;
- EIP-5792/user-op state only if the harness can faithfully resolve their status.

A test should never rely on a production user wallet or a shared mutable test account.

## Core Transaction Matrix

Every material write flow needs assertions for:

| Stage | Required cases |
| --- | --- |
| Preparation | missing/invalid input, unsupported deployment, insufficient balance, expired quote/deadline, failed simulation |
| Wallet | connect required, wrong chain, switch accepted/rejected, signature accepted/rejected, duplicate click |
| Broadcast | hash/operation ID persisted, provider timeout, transaction replacement where supported |
| Confirmation | pending after UI unmount, successful receipt, reverted receipt, dropped/expired user operation or batch |
| Aftermath | precise cache invalidation/refetch, optimistic rollback, indexer lag does not overwrite confirmed state |
| Safety | warning/acknowledgement invalidated by changed action, blocked/critical risk cannot execute |

## DeFi-Specific E2E Assertions

For swaps, deposits, loans, or bridges, assert protocol outcomes:

- exact-in: input decreases within expected gas accounting and output increases by at least the protected minimum;
- exact-out: output meets exact requested quantity and input does not exceed protected maximum;
- slippage/price impact/fee-on-transfer warning appears with manipulated fixtures;
- approval, reset, permit, and action steps occur in required order;
- source confirmation is not reported as destination completion for a bridge/chained operation.

## Test Hygiene

- Give each test one behavior and use semantic locators/test IDs, not fragile DOM structure.
- Await network/chain preconditions explicitly; avoid arbitrary sleeps.
- Keep a debug trace of chain, fork block, transaction hash/reference, and test artifacts only on failure—redacted and isolated from production telemetry.
- Restore all node state, test storage, browser storage, and mock handlers after each test.
- Run focused unit tests locally, then relevant E2E/fork tests in CI. Record flaky RPC/session failures separately from product regressions.

## Source-Derived Patterns

- `apps/web/src/playwright/anvil/anvil-manager.ts`: pinned fork, explicit health checks/backoff, clock synchronization, and recovery at test boundaries rather than mid-test.
- `apps/web/src/playwright/fixtures/anvil.ts`: fresh snapshots per test, checked revert result, base-fee reset, scoped helpers, and a controlled test account.
- `apps/web/src/pages/Swap/Swap/Swap.anvil.e2e.test.ts`: adjust only nondeterministic quote inputs, drive UI flow, and assert real post-transaction balance state so a false success toast cannot pass.
- The `*.anvil.e2e.test.ts`, WalletConnect, and transaction test suites: cover approval/permit sequence, user rejection, connector behavior, chain transaction state, and E2E finality alongside unit-level decision tests.
