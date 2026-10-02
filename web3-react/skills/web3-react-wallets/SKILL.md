---
name: web3-react-wallets
description: Builds reliable EVM wallet connection and account architecture in React with Wagmi. Use for connector setup, connect/disconnect, intentional reconnect, WalletConnect, injected wallets, Safe/iframe wallets, account and chain state, multi-wallet identity, connector errors, wallet capability discovery, or chain switching UX.
---

# Web3 React Wallets

Load `web3-react` for public-client/config rules. This skill owns the user-wallet boundary: connectors, sessions, account identity, connection state, and capability discovery. A connector is not a general RPC backend; wallet clients sign and broadcast while app-owned clients read.

## Design the Wallet Module as a Seam

Feature components should not know connector IDs, WalletConnect storage, iframe quirks, or provider error strings. Put that behavior behind a narrow `WalletConnection` module:

```ts
interface WalletConnection {
  connect(input: { walletId: string }): Promise<{ connected: boolean }>
  disconnect(): Promise<void>
  switchTo(chainId: number): Promise<'switched' | 'already-on-chain' | 'rejected' | 'unsupported'>
}
```

Expected user cancellations resolve to a safe result (`connected: false`, `rejected`); unexpected errors are thrown after redacted logging. The UI uses a singleton mutation so multiple buttons cannot open competing wallet prompts.

Keep app-owned wallet metadata separate from Wagmi connector instances. A product wallet entry can map to a connector ID, display metadata, support policy, and analytics label without leaking those concerns into every feature.

## Account Identity and Scope

An account is not merely an address. Treat its identity as at least:

```ts
type AccountIdentity = {
  platform: 'evm'
  address: `0x${string}`
  walletId: string
  connectorId?: string
}
```

The connected chain is a separate, changing scope. A feature must also carry its **target chain**. Never use a stale address, stale connector client, or current chain implicitly after awaiting connection/switching.

Maintain one normalized account state surface for UI/features with distinct states such as:

- `disconnected`
- `reconnecting` (intentional restore only)
- `connecting` (which wallet is pending)
- `connected` on a supported chain
- `connected` on an unsupported chain
- `switching-chain`
- `error` only for unexpected failures

On account/connector/chain changes, clear or scope account-specific UI state, transaction filters, persisted query data, capability data, and sensitive analytics identity. Do not treat an injected provider's presence as user authorization.

## Connection Rules

1. Configure each supported connector once at application startup; do not instantiate connectors in buttons.
2. Keep wallet order, availability detection, mobile/deep-link policy, and feature support in one wallet registry.
3. Use one connect mutation at a time. Disable/identify the pending wallet option; duplicate connect prompts are a common source of WalletConnect and injected-wallet failures.
4. A user rejecting connect, account selection, or chain switching is cancellation. Preserve the preceding UI state and avoid generic failure telemetry.
5. Validate Safe/iframe origin constraints and only use an iframe connector in its intended embedding context.
6. Disconnect must clear app-owned reconnect intent and account-scoped persisted data; do not rely solely on a connector's storage behavior.
7. Listen to Wagmi account/chain/disconnect state through one updater/provider, then publish normalized state. Do not scatter low-level listeners across screens.

## Intentional Reconnect

Automatic reconnect is a product policy, not a harmless default. Persist only a recent **app-approved connector ID** and use it to choose reconnect candidates. Handle special supported contexts, such as a verified Safe iframe, explicitly.

```ts
const reconnectable = recentConnectorId
  ? connectors.filter((connector) => connector.id === recentConnectorId)
  : []

await reconnect(config, { connectors: reconnectable })
```

Do not reconnect every connector whose `isAuthorized()` probe succeeds: injected-wallet authorization can outlive site-data clearing and surprise-connect a user. Track when reconnect settles so UI does not flash “disconnected” before an intentional restoration attempt completes.

## Chain Switching

The target feature decides its required chain. The wallet module only executes a safe switch:

1. Confirm the chain is product-supported and deployed for the feature.
2. If already on it, return `already-on-chain`; some wallets reject unnecessary switches.
3. Prompt once with clear feature context.
4. Normalize a user rejection as cancellation; do not log/display a generic error.
5. After await, re-read account and chain before signing/simulating. Do not reuse a connector client captured before switching.

Do not silently add unknown chains or ask wallets to switch to a chain just because remote data says so. Chain additions and custom chains need a separately reviewed allowlist and UX.

## Capability Discovery Is Optional and Untrusted Until Validated

Wallet behavior varies by connector, account, and chain. Query capabilities with a timeout, validate/normalize the result, and store an account+connector+chain-scoped snapshot:

```ts
type CapabilityState =
  | { status: 'unknown' }
  | { status: 'unsupported' }
  | { status: 'supported'; atomicBatching: boolean; alternateGasFees: boolean }
  | { status: 'unavailable' } // timeout or malformed response; use conservative fallback
```

- Treat malformed, absent, or timed-out responses as unsupported/unavailable—not as permission to send an advanced request.
- Re-fetch when connector, account, or relevant chain changes.
- Gate EIP-5792 batches, smart-account sponsorship, alternate gas assets, and delegated execution by capability plus product support. Connector name is not a capability check.
- Use a conservative sequential EOA fallback where the feature allows it. If a feature truly requires atomicity, block it rather than silently weakening its invariant.

Load `web3-react-account-abstraction` when the selected capability uses `wallet_sendCalls`, user operations, passkeys, or delegation.

## Wallet Privacy and Observability

Record connection funnel events at semantic milestones: wallet selected, prompt opened, connected, rejected, chain switched, and unexpected failure. Redact provider payloads, URI/session secrets, typed data, and full account history. Clear analytics user properties on disconnect and avoid treating an unsupported chain as a connection failure.

## Test Matrix

Test with real or controlled connectors for:

- initial disconnected state; first connect; rejection; duplicate click while connecting;
- intentional reconnect after refresh; clear-site-data; stale persisted connector; Safe/iframe policy;
- account change, disconnect, chain change, unsupported chain, already-correct chain, and rejected switch;
- WalletConnect session restoration/disconnect where supported;
- capability timeout, malformed response, account/chain refresh, supported batch, and sequential fallback;
- app public reads remaining usable while disconnected and never moving to connector RPC.

## Source-Derived Patterns

- `apps/web/src/components/Web3Provider/createWeb3Provider.tsx` and `connection/mountReconnect.ts`: choose reconnect candidates through app-owned intent rather than indiscriminate injected-wallet restoration.
- `features/wallet/connection/services/createConnectionService.ts` and `connectors/wagmi.ts`: a small connection seam returns `connected: false` for expected cancellation and throws only unexpected errors.
- `features/wallet/connection/hooks/useConnectWalletMutation.tsx`: one singleton connection mutation prevents concurrent prompts and exposes the pending wallet.
- `features/accounts/store/types.ts` and `packages/uniswap/src/features/accounts/store/types/Account.ts`: account identity is platform/address/wallet-aware, not a raw address alone.
- `features/accounts/store/updater.tsx`: publish account/chain lifecycle from a centralized updater and clear/update user identity deliberately.
- `state/walletCapabilities/lib/handleGetCapabilities.ts`: time-bound, validated capability discovery with conservative fallback.
