---
name: web3-react
description: Builds and upgrades production-grade EVM React applications with Viem and Wagmi. Use when setting up a React dapp, configuring wallets or chains, designing Web3 client architecture, migrating from ethers/web3.js, or applying Web3 security, reliability, performance, and testing practices. Load web3-react-onchain-data for reads and data caching; load web3-react-transactions for signatures, approvals, writes, and confirmations.
---

# Production Web3 React Architecture

Build an application that is correct under wallet changes, chain changes, RPC failures, stale indexed data, rejected prompts, and transactions that remain pending after the UI closes. Prefer **Viem + Wagmi + TanStack Query** for new EVM React work.

This skill is the entry point. Before implementing a focused feature, load:

- `../web3-react-onchain-data/SKILL.md` for contract reads, multicalls, logs, indexers, and cache design.
- `../web3-react-transactions/SKILL.md` for simulations, writes, permits, approvals, and transaction lifecycle UX.
- `../web3-react-transaction-engine/SKILL.md` when a flow has durable/multiple steps or must survive navigation and refresh.
- `../web3-react-wallets/SKILL.md` for connectors, intentional reconnect, account identity, and capability discovery.
- `../web3-react-dapp-security/SKILL.md` for pre-signing validation, risk scans, recipient/token/approval safety, and acknowledgement UX.
- `../web3-react-account-abstraction/SKILL.md` for EIP-5792, ERC-4337, EIP-7702, paymasters, and embedded wallets.
- `../web3-react-defi-execution/SKILL.md` for quote freshness, slippage, route validation, and DeFi execution plans.
- `../web3-react-testing/SKILL.md` for unit/integration/Anvil-fork E2E coverage.
- `wagmi-development` only when modifying Wagmi itself rather than consuming it in an application.

## First: Discover, Then Design

Before changing code, establish:

1. Framework and rendering boundary: Vite SPA, Next.js client/server components, Remix, etc.
2. Installed versions of `viem`, `wagmi`, and `@tanstack/react-query`; write to the installed API, not a remembered version.
3. Supported chain IDs, deployment addresses, ABI provenance, RPC policy, wallet connectors, and whether the app supports smart accounts / EIP-5792.
4. The feature's authority model: immutable app config, on-chain state, API/indexer data, or local UI state.
5. The exact transaction and failure states a user can encounter.

Do not add a second Web3 provider, public client, query client, address registry, or transaction store when the application already has an appropriate one. Put chain definitions, addresses, ABIs, RPC policy, and feature support behind narrow shared modules; UI components should consume domain hooks, not construct clients or hardcode deployments.

## Non-Negotiable Boundaries

### 1. Separate public reads from wallet actions

- **Public client / configured Wagmi transport:** reads, logs, simulation, estimates, and event subscriptions. It is app-owned, observable, rate-limited, and works while disconnected.
- **Connector wallet client:** signatures and broadcasts only. Never use a connector RPC endpoint as the general read path.
- Give every read, simulation, and write an explicit target `chainId`. The wallet's current chain is an input to connection UX, not a substitute for a feature's intended chain.

### 2. Make identity part of every state boundary

Wallet address, chain ID, contract address, relevant block / block tag, and feature parameters belong in query identity or are otherwise explicitly scoped. On account or chain change, stale data must not be rendered as belonging to the new identity.

Validate untrusted user input with Viem (`isAddress`, `getAddress`) or a schema at the boundary. Do not paper over missing inputs with `as Address`, `as Hex`, a fake zero address, or an `any` cast.

### 3. Treat external transaction payloads as untrusted

A backend quote, route, or calldata payload may be useful but does not become trusted merely because it is from an API. Validate its schema, chain ID, sender, target, value, deadline, token addresses, spender, expected effects, and feature constraints before displaying or signing it. Never log seed phrases, signatures, raw authentication tokens, or personally sensitive wallet metadata.

## Baseline Provider Shape

Keep config stable at module scope and create the `QueryClient` once. Use a small, intentional connector set and only chains the product really supports.

```tsx
// web3/config.ts
import { mainnet, optimism } from 'wagmi/chains'
import { createConfig, fallback, http } from 'wagmi'
import { injected, walletConnect } from 'wagmi/connectors'

export const wagmiConfig = createConfig({
  chains: [mainnet, optimism],
  connectors: [
    injected(),
    walletConnect({ projectId: import.meta.env.VITE_WALLETCONNECT_PROJECT_ID }),
  ],
  transports: {
    [mainnet.id]: fallback([
      http(import.meta.env.VITE_MAINNET_RPC_PRIMARY, { timeout: 6_000 }),
      http(import.meta.env.VITE_MAINNET_RPC_FALLBACK, { timeout: 6_000 }),
    ]),
    [optimism.id]: http(import.meta.env.VITE_OPTIMISM_RPC_URL, { timeout: 6_000 }),
  },
})

declare module 'wagmi' {
  interface Register {
    config: typeof wagmiConfig
  }
}
```

```tsx
// web3/Web3Providers.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState, type PropsWithChildren } from 'react'
import { WagmiProvider } from 'wagmi'
import { wagmiConfig } from './config'

export function Web3Providers({ children }: PropsWithChildren) {
  const [queryClient] = useState(
    () => new QueryClient({
      defaultOptions: {
        queries: {
          retry: 1,
          staleTime: 15_000,
          refetchOnWindowFocus: true,
        },
      },
    }),
  )

  return (
    <WagmiProvider config={wagmiConfig} reconnectOnMount>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </WagmiProvider>
  )
}
```

Adapt environment-variable syntax and SSR behavior to the framework. Do not expose private RPC/API credentials to browsers; public client-side keys still need origin, quota, and abuse controls.

## Connection and Chain UX

- Model `disconnected`, `reconnecting`, `connected on required chain`, `connected on another chain`, and `connector unavailable` separately.
- Reconnect only intentionally persisted connectors. Do not surprise-connect every injected provider after storage is cleared or in embedded/iframe contexts.
- When a feature needs a different chain, tell the user why, request exactly one switch, and handle rejection as cancellation—not an application error. Recheck account and chain after the await.
- Guard features by a product-owned capability table: supported chain, deployment exists, connector capability, account type, and feature flag. Do not infer support from a chain ID alone.

## Production Requirements

### Reliability

- Centralize RPC endpoints, fallback policy, request timeouts, retry rules, and observability. A public read path should survive a single provider failure without silently mixing chain data.
- Use batching/multicall deliberately for independent reads. Bound concurrency for large multi-chain work.
- Surface fresh/on-chain data separately from indexed or API data when their lag changes a decision. Security or eligibility gates should fail closed when an essential verification read fails.
- Persist only deliberately selected query data. Version/bust persisted caches on schema changes and use BigInt-safe serialization. Never persist secrets, signing payloads, stale quote state, or account-specific data without an account-scoped persistence policy.

### Security and product correctness

- Use audited, versioned ABIs and per-chain deployment registries. Fail unavailable when a deployment is absent.
- Keep base-unit values as `bigint`; use `parseUnits` only at validated form boundaries and `formatUnits` only for display. Never use JS `number` for token amounts, fees, prices, nonces, or block numbers.
- Display chain, recipient/contract, token, amount, approval spender, fees, slippage/deadline, and meaningful warnings before a signature or broadcast.
- A submitted hash means **broadcast**, not success. A receipt means **confirmed**. For cross-chain, intents, user operations, and batches, model their own terminal state instead of pretending a transaction hash is finality.
- Add an error boundary, structured error reporting with redaction, RPC latency/error metrics, and feature/transaction funnel telemetry. User rejection and expected reverts should not page an error tracker.

### Testing

Test pure calldata/value builders and validators first. Then test hooks/components for disabled, loading, error, wrong-chain, rejection, pending, reverted, and confirmed states. For write flows, run an E2E path against Anvil/fork/testnet with a controlled wallet; assert real state changes and receipt handling, not only mocked hook calls.

## Delivery Checklist

Before calling a Web3 feature complete, verify:

- [ ] Explicit chain and account scope in every read/write.
- [ ] Validated ABI, address, calldata, and units; no unsafe casts or placeholder addresses.
- [ ] App-owned public RPC reads; connector only signs/broadcasts.
- [ ] Query key / cache policy matches data volatility and identity.
- [ ] Wrong-chain, disconnect, wallet rejection, RPC outage, revert, and pending-confirmation UX exist.
- [ ] All contracts and derived permissions are revalidated at submit time.
- [ ] Post-confirmation invalidation/refetch is scoped and tested.
- [ ] User-facing labels and warnings make the signing action understandable.
- [ ] Unit, integration, and appropriate E2E checks pass.

## Source-Derived Patterns

For the full audited pattern map and source-path rationale, read [Uniswap Interface Research Notes](references/uniswap-interface-patterns.md).

This skill was distilled from the Uniswap Interface repository (examined at `0d49e580c1`), then generalized rather than copied:

- `apps/web/src/connection/wagmiConfig.ts`: one typed Wagmi config; multichain clients; batched reads; per-request RPC routing; fallback transports; timeout and RPC observability.
- `apps/web/src/components/Web3Provider/createWeb3Provider.tsx`: intentional reconnect policy instead of indiscriminate injected-wallet recovery.
- `apps/web/src/hooks/useEthersProvider.ts`: strict public-read versus connector-signing provider boundary during an ethers-to-Viem migration.
- `packages/chains/src/rpc/ViemClientManager.ts`: avoid lifetime-stale clients when RPC feature/config state can change.
- `packages/react-query/src/createQueryClient.ts` and `packages/uniswap/src/data/reactQuery/SharedPersistQueryClientProvider.web.tsx`: explicit cache defaults, bounded retry, BigInt-safe persistence, cache versioning.
- `apps/web/src/features/transactions/TransactionWatcherProvider.tsx`: transaction confirmation is an application-level event that updates relevant data after the originating UI unmounts.
