# Uniswap Interface Research Notes

**Repository examined:** `/Users/rabuawad/Code/dev-container/moon-mint/tools/interface`  
**Revision:** `0d49e580c1` (`ci(release): publish latest release`)  
**Scope:** Web React application and shared packages, with focused review of Viem/Wagmi, RPC transport, contract reads, React Query, contracts/ABI boundaries, transaction execution, errors, and tests.

This is source material for the `web3-react*` skills. It records design lessons, not a mandate to copy Uniswap's product-specific architecture.

## What Was Examined

The workspace is a Bun/Nx monorepo with the web app at `apps/web`, shared chain/RPC utilities at `packages/chains`, shared React Query/cache/domain code at `packages/uniswap` and `packages/react-query`, and a separate wallet/extension stack. The web package uses React 19, Wagmi 3.6, Viem 2.49, TanStack Query 5.90, Ethers v5 compatibility code, Redux/Sagas, and product-specific APIs.

A broad source inventory found:

- Wagmi/Viem integration in connector/config/provider code, account hooks, contracts, liquidity, auction, swap, and wallet modules.
- 34 `useReadContract` occurrences and 64 multicall occurrences in the scanned web/shared source.
- Dedicated transaction, approval, permit, receipt-watcher, activity, and Anvil/WalletConnect E2E suites.
- A deliberate in-progress migration seam between Ethers/Web3React-facing legacy feature code and Viem/Wagmi-facing provider/config code.

## Architecture Lessons

### 1. One public read plane; wallets are signing planes

**Evidence**

- `apps/web/src/hooks/useEthersProvider.ts`
- `apps/web/src/hooks/useContract.ts`
- `apps/web/src/connection/wagmiConfig.ts`

Uniswap explicitly comments that disconnected/public clients serve reads through its own routed RPC transport, while connector clients are only used for signatures and broadcasts. This prevents a connected wallet SDK from silently changing read endpoints, headers, rate limits, observability, or behavior when a wallet is disconnected.

**Generalized rule**

Use a configured public Viem client/Wagmi transport for all routine reads and simulations. Use the connector-backed wallet client for `writeContract`, `sendTransaction`, and signing only. This remains true even if a legacy Ethers adapter exists during migration.

### 2. Transport configuration is a product reliability boundary

**Evidence**

- `apps/web/src/connection/wagmiConfig.ts`
- `packages/chains/src/rpc/createUniRpcTransport.ts`
- `packages/chains/src/rpc/createUniRpcRoutedTransport.ts`
- `packages/chains/src/rpc/observability/createObservableTransport.ts`
- `packages/chains/src/rpc/ViemClientManager.ts`

The web config builds one client per chain with multicall batching and a polling interval, uses an ordered fallback list for legacy endpoints, observes RPC errors, applies a short timeout, and routes requests according to the *current* RPC config. The comments explain a non-obvious failure: selecting a transport once at app boot captured an unresolved feature flag and pinned users to an obsolete RPC path for the entire session. The client manager similarly reconstructs clients to avoid stale RPC config and stale signer identity after account change.

**Generalized rule**

Centralize chain definitions, endpoint policy, fallbacks, timeout, batching, session/auth requirements, and telemetry. If transport selection can change at runtime, resolve it per request or invalidate/rebuild clients deliberately. Do not pin a dynamic config decision at startup accidentally.

### 3. Reconnect is a security and UX policy, not a default checkbox

**Evidence**

- `apps/web/src/components/Web3Provider/createWeb3Provider.tsx`
- `apps/web/src/connection/mountReconnect.ts`

Uniswap disables Wagmi's automatic reconnect and reconnects only a deliberately selected connector set. The source cites injected-wallet authorization surviving a site-data clear, iframe constraints, and WalletConnect lifecycle concerns.

**Generalized rule**

Persist and restore only intentionally chosen wallet sessions. Treat injected provider presence as wallet availability, not authorization to restore a product session. Test clean storage, iframe/embed, disconnect, and multi-connector behavior.

### 4. Chain and account scopes are never implicit in production data

**Evidence**

- `apps/web/src/hooks/useMultiChainBlockInfo.ts`
- `apps/web/src/features/Liquidity/hooks/useV4PoolsInitializedOnChain.ts`
- `packages/uniswap/src/features/portfolio/api.ts`

The block hook keys queries by chain and block number. The V4 pool hook assigns `chainId` to each contract call. The portfolio data API keys on account, chain, and normalized token address. Explicit scope prevents a currently connected chain from contaminating multi-chain data.

**Generalized rule**

Every read/write must receive the target chain explicitly. Custom React Query keys must include chain, normalized addresses, arguments, and block context when it changes the answer. Account changes must not allow old data to appear under the next account.

### 5. Contract reads are gated and typed, batches expose partial failure

**Evidence**

- `apps/web/src/hooks/useTokenAllowance.ts`
- `apps/web/src/hooks/usePermitAllowance.ts`
- `apps/web/src/lib/hooks/useCurrencyBalance.ts`
- `apps/web/src/features/Liquidity/hooks/useV4PoolsInitializedOnChain.ts`
- `apps/web/src/features/Toucan/Auction/hooks/useRedeemableBalance.ts`

Read hooks enable only when required owner/spender/token/account parameters exist. Contract lists are memoized. The V4 hook evaluates every `useReadContracts` item status and marks an essential pool-availability check as erroneous rather than calling an unavailable pool available. Allowances refresh after relevant confirmation events.

**Generalized rule**

Disable a query until its real inputs are valid; never substitute a zero address. Use audited `as const` ABIs and `bigint`. When multicall results can partially fail, pair each result with its original target and decide whether the feature degrades gracefully or fails closed.

### 6. Indexers and RPC have different authority

**Evidence**

- `apps/web/src/lib/hooks/useCurrencyBalance.ts`
- `packages/uniswap/src/features/portfolio/api.ts`
- `packages/uniswap/src/features/portfolio/portfolioUpdates/fetchOnChainBalances.ts`

The old currency-balance hook uses indexed data as a fallback when the wallet is not synced to a chain. The portfolio refresh path fetches direct on-chain balances and treats USD valuation as best effort: price lookup failure does not erase a confirmed balance.

**Generalized rule**

Use indexed data for discovery/history/aggregates and targeted RPC reads for security/transaction decisions. A price/indexer error cannot turn a confirmed on-chain quantity into zero. Describe the freshness source where a user could otherwise make an unsafe decision.

### 7. Cache correctness requires cancellation, narrow predicates, and reconciliation

**Evidence**

- `packages/uniswap/src/features/dataApi/balances/portfolioCacheUpdater.ts`
- `packages/uniswap/src/features/dataApi/balances/poolPositionCacheUpdater.ts`
- `apps/web/src/features/transactions/TransactionWatcherProvider.tsx`

Before optimistic portfolio updates, the cache updater cancels matching in-flight queries so a pre-mutation response cannot overwrite the new local state. It broad-scans cache variants only through a predicate that checks owner/platform/chain coverage, then invalidates to reconcile. The watcher runs above feature screens, responding when pending transaction records leave the pending set.

**Generalized rule**

Do not optimistically mutate arbitrary query data. Cancel matching fetches, snapshot/rollback exact entries, scope updates to account and chain, then refetch after terminal state. Confirmation watching belongs above a modal/page so it survives navigation.

### 8. Query policy and persistence are explicit

**Evidence**

- `packages/react-query/src/createQueryClient.ts`
- `packages/uniswap/src/data/reactQuery/SharedPersistQueryClientProvider.web.tsx`
- `apps/web/src/components/PersistQueryClient.tsx`

The shared QueryClient has a deliberate freshness/GC/retry policy; it retries selected server errors but not every failure. Persisted cache configuration uses a cache buster, max age, a BigInt-aware serializer, and allowlisted dehydration options.

**Generalized rule**

Specify query staleness, GC, retry, focus/reconnect behavior, persistence allowlist, serialization, max age, and cache version. Persisting arbitrary contract/API responses is a privacy and staleness risk.

## Transaction Lessons

### 9. Validate again at the final boundary

**Evidence**

- `apps/web/src/pages/Liquidity/CreateAuction/hooks/useCreateAuctionSubmit.ts`
- `apps/web/src/pages/Liquidity/CreateAuction/hooks/useLaunchAuctionFlow.ts`

The create-auction flow rechecks connected wallet identity, start time, wallet-bound OAuth verification, on-chain balance, and emission-window validity immediately before requesting executable transaction data. It prefetches the idempotent backend preparation when a review modal opens, but submits only the prepared result and keeps it available after user rejection.

**Generalized rule**

Prefetch to improve latency, but revalidate dynamic data at submit. Backend-generated calldata must be locally schema-validated and semantically constrained before wallet interaction. A rejected wallet prompt is cancellation; retain valid form/prepared state so a retry does not behave like a generic error.

### 10. Broadcast and confirmation are distinct, even in simple flows

**Evidence**

- `apps/web/src/features/Toucan/Auction/hooks/useMigrateSubmit.ts`
- `apps/web/src/state/sagas/createAuction/submitAuctionLaunchSaga.ts`
- `apps/web/src/features/transactions/TransactionWatcherProvider.tsx`

The migration hook tracks a submitted hash, uses `useWaitForTransactionReceipt`, and only updates in-session auction state after success. The launch saga waits for the approval receipt before submitting the final launch transaction. It also distinguishes EIP-5792 batch ID handling from a usable on-chain explorer hash.

**Generalized rule**

Represent awaiting wallet, broadcast, confirming, confirmed, reverted, rejected, and failed independently. Only advance a dependent approval/action sequence after the prior required receipt. An operation/batch identifier is not automatically a transaction hash or finality proof.

### 11. Wallet capabilities are negotiated, not assumed

**Evidence**

- `apps/web/src/state/sagas/createAuction/submitAuctionLaunchSaga.ts`
- `apps/web/src/state/walletCapabilities/*`

The launch flow verifies same-chain requests, selects the required chain, then checks an explicit wallet capability before using atomic `wallet_sendCalls`; otherwise it sends a confirmed sequence.

**Generalized rule**

Gate advanced behavior (atomic batches, smart accounts, sponsored approval, passkeys, delegated calls) by explicit account+chain capability checks with a safe fallback. Never identify capability by connector name alone.

### 12. Error taxonomy protects users and telemetry

**Evidence**

- `apps/web/src/utils/swapErrorToUserReadableMessage.tsx`
- `packages/uniswap/src/features/transactions/errors.ts`
- `apps/web/src/hooks/useSelectChain.ts`

The source walks nested error/cause/original-error structures with cycle protection and distinguishes wallet rejection from actual failure. Transaction errors retain step information and redact/purposefully fingerprint errors for observability. Chain-switch rejection can be deliberately rethrown for a caller that needs cancellation semantics.

**Generalized rule**

Normalize nested Viem/connector errors. Exclude user cancellation from alarming error telemetry. Decode known custom errors into safe, action-specific recovery copy; report unknown errors with redacted chain/method/semantic context only.

## Testing Lessons

**Evidence**

- `apps/web/src/features/Toucan/Auction/hooks/useMigrateSubmit.test.ts`
- `apps/web/src/features/Liquidity/hooks/useV4PoolsInitializedOnChain.test.ts`
- `apps/web/src/pages/Swap/Swap/Swap.anvil.e2e.test.ts`
- `apps/web/src/playwright/anvil/*`
- `apps/web/src/pages/Liquidity/CreateAuction/hooks/useLaunchAuctionFlow.test.ts`

The repository includes hook/component unit tests, transaction and route E2E, WalletConnect E2E, and Anvil fork fixtures. This validates both the pure decision logic and actual transaction/receipt effects.

**Generalized rule**

Unit-test pure calldata/query-key/validation/error-mapping functions. Hook-test loading/error/identity changes. E2E test the on-chain effect, chain switch, user rejection, and pending-to-confirmed state against Anvil/fork/testnet—not only mocked library hooks.

## What Not To Copy Blindly

- **Ethers v5/Web3React adapters:** they exist for compatibility during migration. New EVM features should be native Viem/Wagmi unless a compatibility seam is explicitly required.
- **Redux/Saga orchestration:** appropriate for Uniswap's multi-protocol/multi-platform complexity, but overkill for a normal single-flow dapp. Keep the same explicit state-machine guarantees with a smaller module when possible.
- **Uniswap RPC/session/feature-flag machinery:** copy the *principles* (fallback, timeout, observability, dynamic config safety), not proprietary endpoint/session specifics.
- **Multi-platform abstractions:** Uniswap supports EVM and Solana. A pure EVM application should not add platform types before it has a real non-EVM requirement.
- **Huge global cache predicates:** use them only when many query variants are demonstrably rendered. Prefer canonical query-option factories and exact invalidation for most apps.

## Recommended Application Layers

For a new or upgraded EVM React app, the smallest durable shape is:

1. `web3/config.ts`: chains, transports, connectors, Wagmi module registration.
2. `web3/contracts/`: audited ABI exports and per-chain deployment lookup/feature support.
3. `web3/queries/`: key factories/query-option factories and domain hooks for on-chain/API data.
4. `web3/transactions/`: pure preparation/validation, per-action submit adapters, persistent tracker/watcher, receipt reconciliation, error normalization.
5. `features/<feature>/`: presentational components and feature-specific form state that use those modules.
6. `test/`: deterministic unit tests plus Anvil/fork E2E fixtures for critical calls.
