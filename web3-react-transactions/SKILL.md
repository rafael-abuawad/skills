---
name: web3-react-transactions
description: Implements secure, understandable EVM transaction and signature flows in React with Viem and Wagmi. Use for simulateContract, writeContract, sendTransaction, waitForTransactionReceipt, token approvals, permits/EIP-712, chain switching, transaction state machines, receipt handling, revert/error decoding, post-confirmation cache updates, smart-account batches, or transaction testing.
---

# Web3 React Transactions

Load `web3-react` for app/provider architecture and `web3-react-onchain-data` when the flow owns reads or query invalidation. Load `web3-react-transaction-engine` when the flow has durable/multiple dependent steps or must survive UI unmount. This skill covers execution: a user prompt, a broadcast, confirmation, failure, and post-confirmation reconciliation are different states.

## Safety Contract

Before a wallet prompt, the application must know and show:

- the required chain and connected account;
- exact contract/recipient, call/function, token amounts in base units and human units, ETH `value`, fee implications, spender/allowance where relevant;
- a fresh simulation or equivalent trusted preflight result;
- deadline, slippage, nonce, permit expiration, and any irreversible/risky effect;
- the expected success effect and the recovery/error path.

Do not send arbitrary API-returned `to`, `data`, and `value` fields without validating a schema and product allowlist. A signing endpoint or quote service is not a replacement for local chain, account, expiry, contract, value, and calldata validation.

Never claim that a transaction succeeded when a wallet returns a hash. A hash proves only that a provider accepted a broadcast attempt. Success requires the relevant confirmation/finality condition.

## A Transaction Is a State Machine

At minimum model:

```ts
type TxPhase =
  | 'idle'
  | 'checking'
  | 'switching-chain'
  | 'awaiting-wallet'
  | 'broadcast'
  | 'confirming'
  | 'confirmed'
  | 'reverted'
  | 'rejected'
  | 'failed'
```

For a multi-step flow use an explicit step list (`approve → permit/sign → action`, `source transaction → bridge finality → destination claim`). Advance a dependent step only after the prior required confirmation—not merely after it returns a hash. Persist enough non-sensitive transaction metadata (hash/batch ID, chain, account, feature, timestamp, semantic action) for an app-level watcher to continue status after the modal or route unmounts.

Keep ephemeral form/modal state local. Keep pending transaction records in a feature-level store/service. Keep remote/on-chain state in the query cache. Do not make a component's mounted lifetime the source of truth for an in-flight transaction.

## Preferred Contract Write: Simulate, Then Broadcast

Use a public client for simulation and a connector-backed wallet only for the write. `useSimulateContract` can provide a request that includes estimated gas and exposes execution reverts before the wallet prompt.

```tsx
import { useCallback, useEffect, useState } from 'react'
import { type Address, type Hex, isAddress, getAddress } from 'viem'
import {
  useAccount,
  useSimulateContract,
  useSwitchChain,
  useWaitForTransactionReceipt,
  useWriteContract,
} from 'wagmi'

const counterAbi = [
  {
    type: 'function',
    name: 'increment',
    stateMutability: 'nonpayable',
    inputs: [],
    outputs: [],
  },
] as const

export function useIncrementCounter({ chainId, counter }: { chainId: number; counter?: string }) {
  const { address: account, chainId: connectedChainId, isConnected } = useAccount()
  const { switchChainAsync } = useSwitchChain()
  const { writeContractAsync, isPending: isAwaitingWallet } = useWriteContract()
  const [hash, setHash] = useState<Hex | undefined>()
  const counterAddress: Address | undefined = counter && isAddress(counter) ? getAddress(counter) : undefined
  const ready = isConnected && account !== undefined && counterAddress !== undefined

  const simulation = useSimulateContract({
    address: counterAddress,
    abi: counterAbi,
    functionName: 'increment',
    account,
    chainId,
    query: { enabled: ready },
  })

  const receipt = useWaitForTransactionReceipt({
    chainId,
    hash,
    query: { enabled: hash !== undefined },
  })

  const submit = useCallback(async () => {
    if (!ready || !simulation.data?.request) {
      return
    }

    if (connectedChainId !== chainId) {
      // A rejected switch is user cancellation. Recheck connection/chain after awaiting it.
      await switchChainAsync({ chainId })
      await simulation.refetch()
    }

    // Use only a fresh, successful preflight request tied to the intended account and chain.
    const result = await simulation.refetch()
    if (!result.data?.request) {
      throw result.error ?? new Error('Transaction can no longer be simulated')
    }

    const transactionHash = await writeContractAsync(result.data.request)
    setHash(transactionHash)
    // Immediately register hash + account + chain + semantic action in the app transaction tracker.
  }, [chainId, connectedChainId, ready, simulation, switchChainAsync, writeContractAsync])

  useEffect(() => {
    if (receipt.isSuccess) {
      // Invalidate/refetch narrowly scoped balances, allowances, positions, and indexer queries here.
      // Mark the persisted transaction confirmed here, not at writeContractAsync().
    }
  }, [receipt.isSuccess])

  return { submit, simulation, hash, receipt, isAwaitingWallet }
}
```

Adapt exact options to the installed Wagmi version. In real code, avoid a closure that can submit an old request: on submit, revalidate the latest form data, account, chain, deadline, quote/version, allowance/nonce, and simulation. Disable duplicate submission while switching, awaiting the wallet, broadcasting, or confirming.

For raw native transfers use `useSendTransaction` with the same chain validation, simulation/estimate policy, broadcast tracking, and receipt lifecycle. For custom user operations, EIP-5792 `wallet_sendCalls`, intents, or relayed transactions, use an adapter that exposes the same semantic phases; a batch ID or operation ID is not necessarily an explorer transaction hash.

## Validation and Simulation Rules

- Perform pure validation synchronously: parsed/normalized addresses, `parseUnits` inputs, amount > 0, balances, recipient rules, supported deployment, feature flag, deadline, and domain constraints.
- Perform on-chain preflight as late as practical. A quote/allowance/pool can change after a modal opens.
- Pass the intended `account`, `chainId`, `value`, and all call args to simulation; simulating from a different account can hide permissions or balance failures.
- Present a simulation revert as actionable UX where possible. Do not prompt a wallet anyway unless the product has a documented reason.
- Treat gas estimates as estimates. Respect user-controlled fee settings only after validation and clear UX; do not blindly multiply them or overwrite EIP-1559 fields.
- After a chain switch, account switch, or any awaited asynchronous precondition, re-read and resimulate. The old closure/result may no longer be valid.

## Approvals and Permits

An ERC-20 approval is a distinct security decision, not invisible setup work.

1. Read allowance on the exact token chain for `{ owner, spender }`.
2. Explain the spender, token, amount, and whether approval is exact or recurring/unlimited.
3. Prefer exact approval where UX permits; use a broad approval only with explicit product rationale and warning.
4. Confirm the approval receipt before submitting the dependent action. Refetch allowance afterward.
5. For tokens that require setting allowance to zero first, model reset and set as two separately confirmed steps.
6. Do not assume tokens return standard behavior; simulation and receipt handling must surface nonstandard/reverting tokens.

For EIP-2612/Permit2/EIP-712 signatures:

- Obtain and validate on-chain nonce/allowance when the protocol requires it.
- Build a typed domain with the exact chain ID and verifying contract. Include a bounded expiration/deadline and display the semantic authorization.
- Treat signature rejection as cancellation, not a generic error. Never log raw signatures.
- A permit signature is not the same as consumed approval; after the consuming transaction confirms, refresh both allowance and feature state.

## Errors: Classify Before Displaying or Reporting

Unwrap nested Viem/wallet errors (`BaseError`, `cause`, connector payloads) with cycle protection. Normalize them into categories:

| Category | UX / telemetry behavior |
| --- | --- |
| User rejected wallet prompt or chain switch | Return to actionable state; do not show a scary failure or report as product error. |
| Validation/preflight revert | Show a specific correction or safe fallback; retain form input where safe. |
| RPC/network/timeout | Offer retry and preserve unsent state; instrument provider/chain/method without sensitive payloads. |
| Broadcast failure / replacement / dropped transaction | Keep hash/nonce context; reconcile from chain rather than assuming terminal failure. |
| Confirmed revert | Mark failed, explain known custom error if decoded, and invalidate/re-read state. |
| Unknown/invariant failure | Give safe generic copy, attach redacted structured diagnostics, and report once. |

Decode custom Solidity errors from the ABI where possible. Do not expose raw RPC errors, calldata, stack traces, secrets, or arbitrary remote strings directly to users.

## Confirmation, Finality, and Cache Reconciliation

- Store `{ hash, chainId, account, action, submittedAt }` immediately after broadcast.
- Use `useWaitForTransactionReceipt` or an app watcher for on-chain actions. Configure required confirmation count/finality for the operation's risk.
- Handle replacement/speed-up/cancel if the wallet/provider stack supports it; a replacement hash should update the tracked record.
- After confirmed success, invalidate/refetch only the relevant account+chain+contract queries. Update indexed/API activity asynchronously; indexer lag must not flip a confirmed action back to pending.
- Roll back failed optimistic state and always do a final targeted reconciliation after terminal error.
- For cross-chain operations, model source confirmation, relay status, destination confirmation, and claimability separately.

## Testing Matrix

For every execution flow, test:

- invalid address/amount, missing account, unsupported chain/deployment, wrong chain, and expired/stale quote;
- successful simulation and simulation revert/custom error;
- rejected chain switch and rejected signature;
- wallet prompt pending, broadcast hash recorded, refresh/unmount while pending, receipt success, receipt revert, RPC timeout, and retry;
- sequential approval/permit/action ordering, allowance refresh, and duplicate-click prevention;
- cache invalidation/optimistic rollback scoped to the originating account and chain;
- E2E against Anvil/fork/testnet with a real encoded call and assertion of post-receipt contract state.

## Execution Checklist

- [ ] Product validates destination, chain, account, values, ABI, calldata, deadline, and permissions.
- [ ] Simulation uses the actual account/chain/value and is refreshed just before broadcast.
- [ ] Chain switching is explicit; rejection is cancellation; state is rechecked after await.
- [ ] Wallet pending, broadcast, confirmation, success, revert, and retryable failure are distinct.
- [ ] Hash/batch metadata outlives the component and does not contain secrets/signatures.
- [ ] Dependent steps wait for required confirmations.
- [ ] Success is receipt/finality-backed and narrowly reconciles caches.
- [ ] Error reporting is classified and redacted; user rejection is excluded from failure telemetry.
- [ ] Unit/integration/E2E tests cover the full state machine.

## Source-Derived Patterns

For broader source rationale, read [Uniswap Interface Research Notes](../web3-react/references/uniswap-interface-patterns.md).

Generalized from Uniswap Interface source (examined at `0d49e580c1`):

- `apps/web/src/features/Toucan/Auction/hooks/useMigrateSubmit.ts`: chain selection → wallet send → tracked hash → receipt confirmation → optimistic in-session state; it never equates send with confirmation.
- `apps/web/src/pages/Liquidity/CreateAuction/hooks/useCreateAuctionSubmit.ts` and `useLaunchAuctionFlow.ts`: validate at the final pre-submit boundary, precompute idempotent transaction data, retain prepared state across a rejection, and distinguish preparation, wallet action, and confirmed success.
- `apps/web/src/state/sagas/createAuction/submitAuctionLaunchSaga.ts`: model dependent approvals and the final call as ordered steps; wait for confirmations; use account capability only for consciously supported atomic batches.
- `apps/web/src/hooks/usePermitAllowance.ts`: read nonce/allowance, build a bounded typed-data permit, and normalize wallet rejection without treating it as a product failure.
- `apps/web/src/utils/swapErrorToUserReadableMessage.tsx` and `packages/uniswap/src/features/transactions/errors.ts`: classify nested wallet/provider errors, avoid false error telemetry for cancellation, and map known failure types to action-specific user copy.
- `apps/web/src/features/transactions/TransactionWatcherProvider.tsx`: confirmation/invalidation belongs to an app-level lifecycle, so it continues after the originating UI route closes.
