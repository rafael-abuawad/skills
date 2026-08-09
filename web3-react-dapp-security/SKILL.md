---
name: web3-react-dapp-security
description: Adds client-side safety controls to EVM React dapps: pre-signing transaction validation, wallet/risk scanning, approval and recipient warnings, token-risk handling, phishing-resistant confirmation UX, blocked-address policy, and privacy-safe telemetry. Use when users may sign, approve, transfer, swap, bridge, or submit externally generated calldata.
---

# Web3 React Dapp Security

This skill addresses the client-side safety layer around smart-contract security. It does not replace an audit, server-side access control, protocol invariants, or wallet-level protections. Load `web3-react-transactions` for execution and `web3-react-onchain-data` for verified reads.

## Threat Model Before UI

For each signing surface, write down:

- **Origin:** user input, app-generated calldata, trusted backend quote, third-party route, connected dapp, or wallet request.
- **Authority:** which chain, account, contract/deployment, token, spender, recipient, and deadline are allowed.
- **Asset effect:** spend, approve, transfer, delegate, wrap, bridge, create order, or sign off-chain authorization.
- **Worst outcome:** unlimited approval, malicious recipient, wrong chain, stale quote, fee-on-transfer loss, spoofed token, replayable signature, or silently failed operation.
- **Control:** block, require revalidation, require explicit acknowledgement, warn, or log/review.

A warning is not a security boundary. Enforce hard product invariants in validated preparation/execution code before a wallet prompt.

## Pre-Signing Policy Pipeline

Build one deterministic policy pipeline for every executable action:

```text
validate schema + address + chain + account
 → verify deployment/allowlist and semantic constraints
 → simulate with the actual account/value
 → risk scan / token / recipient / compliance checks
 → classify: block | requires acknowledgement | allow
 → bind acknowledgement to an immutable action digest
 → display review → request wallet
```

The pipeline must run against the final action. If token, amount, chain, recipient, spender, calldata, value, quote, or deadline changes, previous acknowledgement is invalid and the action must be rescanned/re-reviewed.

### Validate remote execution data

For backend/aggregator/dapp-provided `{ chainId, from, to, data, value }`:

- Parse with a strict schema; reject unknown/invalid numeric, hex, and address values.
- Require expected chain and current account match. Do not trust a remote `from`.
- Require target contracts/deployment paths appropriate for the chosen feature; validate native value bounds.
- Decode known call data against audited ABI where possible and compare semantic token/amount/recipient/spender/deadline values with the review model.
- Validate freshness: request ID/quote digest, expiration, nonce, and configuration version.
- Simulate the exact action. A successful scan does not make an unsimulated or stale action safe.

Never bypass these checks because an API is “first-party.” Do not log raw calldata, scan payloads, session tokens, signatures, recovery material, or full provider error objects.

## Risk Scans: Gate Deliberately

A transaction/signature scanner is advisory but valuable when users can sign arbitrary or high-value actions.

- Make scans a query keyed by chain, normalized account, origin/domain, and a hash of large calldata—not raw calldata in cache keys or telemetry.
- Use a short bounded freshness period and no blind retries for a hard scan failure.
- Explicitly choose policy per surface:
  - **Hard-gated:** dapp request, unknown approval/delegation, high-risk transfer. Confirm stays disabled until scan returns; critical risk requires a distinct acknowledgement or blocks outright.
  - **Fail-safe warning:** app-owned, fully constrained operation where scanner outage should not make the app unusable; preserve other hard invariants and disclose unavailable scan.
- Scanning `loading` is not “no risk.” Distinguish unknown, none, warning, critical, scanner unavailable, and malformed response.
- Acknowledgement must be tied to a stable digest of the scanned action and expire when the action changes.

## Approvals and Delegations

Treat an approval/permit/delegation as its own high-impact action.

- Display token, spender contract/name/address, chain, amount/allowance policy, duration/expiration, and whether it is recurring/unlimited.
- For unknown or unverified sites/contracts, elevate review. Never let a familiar protocol badge vouch for an unrelated requesting origin.
- Inspect all spenders. A single-spender UI shortcut is valid only after verifying exactly one normalized spender exists.
- For ERC-20 reset-to-zero tokens, show reset and set as separate steps and receipts.
- EIP-2612/Permit2/EIP-712 signatures must bind exact `chainId`, verifying contract, owner, nonce, amount, spender, and bounded deadline. Do not store raw signatures.
- Delegation/EIP-7702 changes account execution semantics; require its own explicit, comprehensible confirmation and capability checks.

## Recipient and Token Protection

Use different safety decisions for different risks:

| Risk | Recommended treatment |
| --- | --- |
| Recipient equals sender | Block or require a clear correction flow. |
| New recipient | Show the exact address/name and a friction/confirmation step for material transfers. |
| Recipient is a contract | Show a contract-recipient warning; do not promise recovery. |
| Blocked/compliance-restricted address | Enforce policy before execution; never rely only on a modal. |
| Token blocked/malicious | Block. |
| Honeypot, severe fee-on-transfer, impersonator, spam | High warning or block based on product policy; show concrete effect when known. |
| Non-default/unverified token | Low-friction warning with chain/address and research context. |

Maintain a pure classifier that maps multiple source signals to one severity with documented precedence. Signals may include signed token lists, verified metadata, simulation output, fee-on-transfer data, phishing/risk providers, and product blocklists. One source failure must not turn a high-confidence block into “safe.”

## Confirmation UX That Resists Misuse

- Present critical facts before wallet UI: operation, chain, recipient/contract, asset amount, spender, fees, expiry, and irreversible effects.
- Use descriptive buttons: “Approve USDC for Router,” “Send 1.2 ETH,” not “Confirm.”
- For severe risk, require a separate deliberate acknowledgement after the user has seen the specific warning; do not auto-dismiss it after an unrelated action.
- Make the safe/cancel action visually and keyboard-accessibly available. Do not use dark patterns or countdowns to pressure signing.
- User rejection is cancellation. Do not mislabel it as a transaction failure, but preserve unsent form state safely.

## Security Tests

Test pure classifiers and policy decisions with a severity matrix. Integration/E2E test that:

- scan loading/unavailable/critical states cannot accidentally enable a gated action;
- changing any action field invalidates acknowledgement;
- malformed remote payload, wrong chain/from, expired quote, unknown spender, and failed simulation block execution;
- a single normalized spender is displayed only when truly singular;
- token/recipient warning precedence works; blocked targets cannot be bypassed;
- raw signatures, calldata, credentials, and sensitive scan results never enter logs, analytics, URL params, or persisted cache.

## Source-Derived Patterns

- `packages/wallet/src/features/dappRequests/utils/riskUtils.ts`: a confirm action stays disabled while scan state is unknown or critical risk lacks acknowledgement.
- `packages/wallet/src/features/dappRequests/hooks/useBlockaidTransactionScan.ts`: cache scanner work with a hashed payload component and bounded freshness rather than raw calldata in a query key.
- `packages/wallet/src/features/dappRequests/hooks/useApprovalContractInfo.ts`: derive spender display from normalized, singular approval data and keep site trust separate from contract identity.
- `apps/web/src/pages/Swap/Send/*SpeedBump.tsx`: recipient novelty and contract-recipient risk deserve different friction/copy.
- `packages/uniswap/src/features/tokens/warnings/safetyUtils.ts`: prioritize overlapping token signals into consistent blocked/high/medium/low severity.
- `apps/web/src/hooks/useAccountRiskCheck.ts`: policy checks wait for a resolved result rather than treating loading as permitted.
