---
name: web3-react-onchain-data
description: Implements reliable on-chain reads and Web3 data layers in React with Viem, Wagmi, and TanStack Query. Use for useReadContract/useReadContracts, multicalls, balances, allowances, block data, logs/events, indexer/API reconciliation, cache keys, invalidation, polling, query persistence, or multi-chain reads.
---

# Web3 React On-Chain Data

Load `web3-react` first if the application does not already have a sound Wagmi/public-client architecture. Use this skill for data reads—not signing or writes; load `../web3-react-transactions/SKILL.md` for those.

## Data Authority and Freshness

Classify every displayed value before implementing it:

| Need | Preferred source | Notes |
| --- | --- | --- |
| Contract permission, balance available to spend, nonce, claim eligibility, invariant | direct on-chain RPC read | Security/transaction gates fail closed on an essential read error. |
| Token metadata/deployment | versioned local registry or verified metadata service | Validate chain/address; do not let an unverified logo/list imply safety. |
| Portfolio, history, charts, search, aggregate totals | indexed/API data | Fast and rich, but potentially stale or incomplete. Label/reconcile when a decision depends on it. |
| Current operation inputs | local form state | Parse and validate at the boundary; it is never an authority for execution. |
| A just-submitted transaction's effect | scoped optimistic cache plus receipt/event/on-chain reconciliation | Never claim final success from broadcast alone. |

Use the configured app public client/Wagmi transport for reads. It works while a wallet is disconnected and prevents connector-specific RPC limits or wrong endpoints from becoming your backend.

## Rules for Every Contract Read

1. **Make `chainId` explicit.** A token/deployment's chain is usually the right value; do not silently use the wallet's selected chain for multi-chain views.
2. **Validate addresses before the hook/query is enabled.** Preserve the absence as `undefined`; never use `0x000…` or an unsafe cast to satisfy types.
3. **Use a constant, typed ABI** (`as const`, generated ABI, or audited package export). Do not parse arbitrary ABI JSON inside a rendering component.
4. **Key identity by all material inputs.** For custom queries this normally includes operation, chain ID, normalized address(es), function args, and block tag/number when relevant.
5. **Choose a freshness policy from chain behavior.** Immutable block data can be cached long; an allowance in a submission flow may need a block-level refresh; a historical chart should not poll at all.
6. **Preserve `bigint` end-to-end.** Convert at formatting boundaries, never through `number`.
7. **Represent error and loading separately from absent/zero.** An RPC failure must not become a zero balance or “not eligible.”

## Single Read Pattern

Use Wagmi contract hooks for ordinary reactive reads. Gate via `query.enabled`; do not conditionally call a hook.

```tsx
import { useMemo } from 'react'
import { type Address, erc20Abi, formatUnits, getAddress, isAddress } from 'viem'
import { useReadContract } from 'wagmi'

type Erc20BalanceArgs = {
  chainId: number
  token?: string
  account?: string
  decimals?: number
}

export function useErc20Balance({ chainId, token, account, decimals }: Erc20BalanceArgs) {
  const tokenAddress = useMemo<Address | undefined>(
    () => (token && isAddress(token) ? getAddress(token) : undefined),
    [token],
  )
  const accountAddress = useMemo<Address | undefined>(
    () => (account && isAddress(account) ? getAddress(account) : undefined),
    [account],
  )
  const enabled = tokenAddress !== undefined && accountAddress !== undefined

  const query = useReadContract({
    address: tokenAddress,
    abi: erc20Abi,
    functionName: 'balanceOf',
    args: accountAddress ? [accountAddress] : undefined,
    chainId,
    query: {
      enabled,
      staleTime: 12_000,
    },
  })

  return {
    raw: query.data,
    display: query.data !== undefined && decimals !== undefined ? formatUnits(query.data, decimals) : undefined,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
  }
}
```

Adapt optional parameters to the exact installed Wagmi typings. The invariant is the important part: unavailable inputs disable the query, and no request contains substitute addresses.

For a one-off non-React action, or a domain query that combines multiple RPC/API calls, use `getPublicClient(config, { chainId })` / an app-owned `PublicClient` inside a `queryOptions` factory. Throw clear errors for missing clients or inputs; do not return fake values.

```ts
const tokenBalanceKey = (chainId: number, token: Address, account: Address) =>
  ['erc20Balance', chainId, token.toLowerCase(), account.toLowerCase()] as const
```

Prefer query-option factories shared by prefetching, components, and post-transaction invalidation. They prevent subtle key drift.

## Batched Reads and Multicall

Use `useReadContracts` / `publicClient.multicall` for independent calls on the **same chain**. Build the contracts list from validated inputs, memoize it, and preserve the result-to-input association.

```tsx
const contracts = useMemo(
  () =>
    tokens.map((address) => ({
      address,
      abi: erc20Abi,
      functionName: 'balanceOf' as const,
      args: [account] as const,
      chainId,
    })),
  [tokens, account, chainId],
)

const balances = useReadContracts({
  contracts,
  query: { enabled: tokens.length > 0 && account !== undefined },
})
```

- Do not use one RPC request per table row.
- Split large batches according to provider/calldata limits; bound concurrent batches.
- A multicall can partially fail. Inspect each result's `status`; map it back by index or an explicit ID.
- For a gate that needs *all* calls, a partial result is an error and the UI should fail closed. For a discovery list, preserve successful entries and clearly expose degraded data.
- Multicall does not span chains. Group requests by chain, use one query/client per chain, and merge only at a domain boundary.

## Blocks, Polling, and Event-Driven Freshness

Use the least expensive correctness mechanism:

- **Immutable historical block/receipt:** cache with a long `staleTime`.
- **Live-but-not-critical display:** poll at a chain-aware interval, pause/refetch appropriately when visibility or network state changes.
- **One current-block signal shared by many components:** centralize it; do not give every row its own websocket/polling subscription.
- **Relevant event is available:** watch/filter only that event and invalidate the exact affected queries.
- **Transaction just confirmed:** invalidate/refetch the feature's balance, allowance, position, and API/indexer queries after confirmation.

```tsx
useWatchContractEvent({
  address: token,
  abi: erc20Abi,
  eventName: 'Transfer',
  args: { to: account },
  chainId,
  enabled: Boolean(token && account),
  onLogs: () => {
    void queryClient.invalidateQueries({ queryKey: tokenBalanceKey(chainId, token, account) })
  },
})
```

Keep watcher ownership high enough in the tree that it is not mounted once per list item. Reorgs, dropped websocket connections, and missed events still require periodic or focus/confirmation reconciliation for important values.

Use `blockTag: 'pending'` only when a documented feature genuinely needs pending-state prediction and the selected RPC supports it. Make its provisional nature explicit; ordinary portfolio data should use confirmed/latest state.

## Indexer/API + On-Chain Reconciliation

A top-tier dapp often needs both data sources:

1. Render indexer/API data for history, search, and broad portfolio views.
2. Read targeted on-chain state for the action the user is about to take.
3. After confirmation, update/invalidate the exact account/chain/token cache entries.
4. Reconcile with the indexer asynchronously; do not overwrite a confirmed on-chain result with an older API response.

If doing an optimistic mutation:

- `cancelQueries` for exactly matching keys first, so in-flight pre-action responses cannot clobber the optimistic write.
- Snapshot only the affected cached entries for rollback.
- Write an account/chain-scoped optimistic state.
- Roll back on broadcast/receipt failure; invalidate after either terminal outcome to reconcile.
- Broad cache scans are sometimes necessary for filtered query variants, but write a tested predicate that matches owner, platform, and chain coverage. Do not mutate every portfolio cache.

Persisted React Query data must have a version/buster, max age, a serialization policy that supports `bigint`, and an allowlist. Scope account-specific persistence by account or clear it on account change; never persist signing state, signatures, secrets, or short-lived executable quotes.

## Data-Layer Checklist

- [ ] Direct read versus indexed/API data is intentional and visible where material.
- [ ] Query is disabled, not fabricated, until validated parameters exist.
- [ ] Chain/address/account/args are represented in key scope or hook config.
- [ ] `bigint` is retained; decimals and formatting are correct.
- [ ] Batches are same-chain, bounded, and partial failures are handled.
- [ ] Polling/event subscriptions have one clear owner and cleanup/reconciliation behavior.
- [ ] Confirmation invalidates only relevant cache entries; optimistic updates cannot be clobbered by races.
- [ ] Tests cover absent input, zero value, RPC error, partial multicall failure, account/chain switch, and post-transaction freshness.

## Source-Derived Patterns

For broader source rationale, read [Uniswap Interface Research Notes](../web3-react/references/uniswap-interface-patterns.md).

Generalized from Uniswap Interface source (examined at `0d49e580c1`):

- `apps/web/src/hooks/useTokenAllowance.ts` and `usePermitAllowance.ts`: a read is explicitly enabled only with owner/spender/address inputs and is refreshed when the relevant transaction type confirms.
- `apps/web/src/lib/hooks/useCurrencyBalance.ts` and `features/Liquidity/hooks/useV4PoolsInitializedOnChain.ts`: typed `useReadContracts`, stable construction, same-chain batching, positional result checks, and fail-closed eligibility behavior.
- `apps/web/src/hooks/useMultiChainBlockInfo.ts`: explicit per-chain query keys, block-specific freshness, parallel multi-chain requests, and immutable historical timestamp caching.
- `packages/uniswap/src/features/portfolio/api.ts` and `portfolioUpdates/fetchOnChainBalances.ts`: on-chain balance refreshes are distinct from indexed portfolio data; best-effort price enrichment must not erase a confirmed balance.
- `packages/uniswap/src/features/dataApi/balances/portfolioCacheUpdater.ts`: cancel matching in-flight queries before an optimistic write, update all relevant filtered variants with a narrow predicate, then reconcile.
- `packages/react-query/src/createQueryClient.ts`: bounded retry policy and explicit freshness/cache defaults rather than accidental global behavior.
