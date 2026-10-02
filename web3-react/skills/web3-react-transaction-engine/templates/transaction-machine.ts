/**
 * Framework-agnostic transaction ledger state machine.
 *
 * Copy this into an app-owned `web3/transactions` module. It deliberately does
 * not import React, Wagmi, Viem, a database, or a UI library. A runner adapts
 * wallet actions into events; a root-level watcher adapts receipts/operation
 * status into events; React subscribes to the persisted ledger.
 *
 * Never put calldata, typed-data payloads, signatures, private keys, session
 * tokens, or arbitrary backend responses in TransactionRecord.metadata. This
 * record is designed to be safe to persist and inspect.
 */

export type TransactionPhase =
  | 'ready'
  | 'awaiting-wallet'
  | 'submitted'
  | 'confirming'
  | 'confirmed'
  | 'rejected'
  | 'reverted'
  | 'failed'

export type TransactionStepKind = 'signature' | 'transaction' | 'operation'

export type TransactionReference =
  | { kind: 'transaction'; chainId: number; hash: `0x${string}` }
  | { kind: 'user-operation'; chainId: number; userOpHash: `0x${string}`; transactionHash?: `0x${string}` }
  | { kind: 'wallet-call'; chainId: number; batchId: string; transactionHash?: `0x${string}` }

/** Serializable, redacted receipt details. Keep quantities as strings for JSON persistence. */
export type Confirmation = {
  blockNumber?: string
  blockHash?: `0x${string}`
  transactionHash?: `0x${string}`
  confirmedAt: number
}

export type TransactionFailure = {
  /** Stable application category: rejected, rpc, validation, revert, unknown, etc. */
  category: string
  /** Safe, user-displayable summary—not raw RPC/provider payload. */
  message: string
}

export type TransactionStep = {
  id: string
  label: string
  kind: TransactionStepKind
  /** Steps begin in order. A later step may not request a wallet action early. */
  phase: TransactionPhase
  reference?: TransactionReference
  confirmation?: Confirmation
  failure?: TransactionFailure
  updatedAt: number
}

export type TransactionRecord = {
  version: 1
  id: string
  action: string
  account: `0x${string}`
  chainId: number
  /** Caller-owned key for deduping the same semantic action. Do not derive from JSON.stringify. */
  dedupeKey?: string
  phase: TransactionPhase
  steps: readonly TransactionStep[]
  createdAt: number
  updatedAt: number
  /** Small, serializable display/analytics data only. */
  metadata: Readonly<Record<string, string | number | boolean | null>>
}

export type TransactionEvent =
  | { type: 'step-requested'; stepId: string; at: number }
  | { type: 'step-submitted'; stepId: string; reference: TransactionReference; at: number }
  | { type: 'step-confirming'; stepId: string; at: number }
  | { type: 'step-confirmed'; stepId: string; confirmation: Confirmation; at: number }
  | { type: 'step-rejected'; stepId: string; failure: TransactionFailure; at: number }
  | { type: 'step-reverted'; stepId: string; failure: TransactionFailure; confirmation?: Confirmation; at: number }
  | { type: 'step-failed'; stepId: string; failure: TransactionFailure; at: number }
  | {
      type: 'reference-resolved'
      stepId: string
      transactionHash: `0x${string}`
      confirmation?: Confirmation
      at: number
    }
  | { type: 'flow-failed'; failure: TransactionFailure; at: number }

export function createTransactionRecord(input: {
  id: string
  action: string
  account: `0x${string}`
  chainId: number
  steps: ReadonlyArray<Pick<TransactionStep, 'id' | 'label' | 'kind'>>
  metadata?: Readonly<Record<string, string | number | boolean | null>>
  dedupeKey?: string
  at: number
}): TransactionRecord {
  if (input.steps.length === 0) {
    throw new Error('A transaction flow needs at least one step')
  }
  if (new Set(input.steps.map((step) => step.id)).size !== input.steps.length) {
    throw new Error('Transaction step ids must be unique')
  }

  return {
    version: 1,
    id: input.id,
    action: input.action,
    account: input.account,
    chainId: input.chainId,
    dedupeKey: input.dedupeKey,
    phase: 'ready',
    steps: input.steps.map((step) => ({ ...step, phase: 'ready', updatedAt: input.at })),
    createdAt: input.at,
    updatedAt: input.at,
    metadata: input.metadata ?? {},
  }
}

/** Returns the next non-confirmed step. A runner must not skip it. */
export function getCurrentStep(record: TransactionRecord): TransactionStep | undefined {
  return record.steps.find((step) => step.phase !== 'confirmed')
}

export function isTerminalPhase(phase: TransactionPhase): boolean {
  return phase === 'confirmed' || phase === 'rejected' || phase === 'reverted' || phase === 'failed'
}

/**
 * Pure reducer. Persist its result before running any follow-up effect.
 *
 * `step-rejected` intentionally finishes this attempt. Create a new record for
 * a fresh user attempt rather than mutating an old rejection into success; this
 * preserves an accurate activity history and keeps deduplication deliberate.
 */
export function reduceTransaction(record: TransactionRecord, event: TransactionEvent): TransactionRecord {
  if (isTerminalPhase(record.phase)) {
    throw new Error(`Cannot apply ${event.type} to terminal transaction ${record.id}`)
  }

  if (event.type === 'flow-failed') {
    return {
      ...record,
      phase: 'failed',
      updatedAt: event.at,
      steps: record.steps.map((step) =>
        step.phase === 'ready'
          ? { ...step, phase: 'failed', failure: event.failure, updatedAt: event.at }
          : step,
      ),
    }
  }

  const index = record.steps.findIndex((step) => step.id === event.stepId)
  if (index === -1) {
    throw new Error(`Unknown transaction step ${event.stepId}`)
  }
  const current = record.steps[index]
  const previous = record.steps.slice(0, index)

  if (event.type === 'step-requested' && previous.some((step) => step.phase !== 'confirmed')) {
    throw new Error(`Cannot start ${event.stepId} before all prior steps confirm`)
  }

  const nextStep = transitionStep(current, event)
  const steps = record.steps.map((step, stepIndex) => (stepIndex === index ? nextStep : step))
  return {
    ...record,
    phase: derivePhase(steps),
    steps,
    updatedAt: event.at,
  }
}

function transitionStep(step: TransactionStep, event: Exclude<TransactionEvent, { type: 'flow-failed' }>): TransactionStep {
  switch (event.type) {
    case 'step-requested':
      assertPhase(step, ['ready'], event)
      return { ...step, phase: 'awaiting-wallet', updatedAt: event.at }
    case 'step-submitted':
      assertPhase(step, ['awaiting-wallet'], event)
      if (step.kind === 'signature') {
        throw new Error(`Signature step ${step.id} cannot be submitted on-chain`)
      }
      return { ...step, phase: 'submitted', reference: event.reference, updatedAt: event.at }
    case 'step-confirming':
      assertPhase(step, ['submitted'], event)
      return { ...step, phase: 'confirming', updatedAt: event.at }
    case 'step-confirmed':
      assertPhase(step, ['awaiting-wallet', 'submitted', 'confirming'], event)
      return {
        ...step,
        phase: 'confirmed',
        confirmation: event.confirmation,
        failure: undefined,
        updatedAt: event.at,
      }
    case 'step-rejected':
      assertPhase(step, ['awaiting-wallet'], event)
      return { ...step, phase: 'rejected', failure: event.failure, updatedAt: event.at }
    case 'step-reverted':
      assertPhase(step, ['submitted', 'confirming'], event)
      return {
        ...step,
        phase: 'reverted',
        failure: event.failure,
        confirmation: event.confirmation,
        updatedAt: event.at,
      }
    case 'step-failed':
      assertPhase(step, ['ready', 'awaiting-wallet', 'submitted', 'confirming'], event)
      return { ...step, phase: 'failed', failure: event.failure, updatedAt: event.at }
    case 'reference-resolved':
      assertPhase(step, ['submitted', 'confirming'], event)
      if (!step.reference || step.reference.kind === 'transaction') {
        throw new Error(`Step ${step.id} does not have a resolvable operation reference`)
      }
      const reference = { ...step.reference, transactionHash: event.transactionHash }
      return {
        ...step,
        reference,
        ...(event.confirmation
          ? { phase: 'confirmed' as const, confirmation: event.confirmation }
          : { phase: 'confirming' as const }),
        updatedAt: event.at,
      }
  }
}

function assertPhase(step: TransactionStep, allowed: readonly TransactionPhase[], event: TransactionEvent): void {
  if (!allowed.includes(step.phase)) {
    throw new Error(`Cannot apply ${event.type} to step ${step.id} in phase ${step.phase}`)
  }
}

function derivePhase(steps: readonly TransactionStep[]): TransactionPhase {
  if (steps.some((step) => step.phase === 'failed')) return 'failed'
  if (steps.some((step) => step.phase === 'reverted')) return 'reverted'
  if (steps.some((step) => step.phase === 'rejected')) return 'rejected'
  if (steps.every((step) => step.phase === 'confirmed')) return 'confirmed'
  if (steps.some((step) => step.phase === 'awaiting-wallet')) return 'awaiting-wallet'
  if (steps.some((step) => step.phase === 'confirming')) return 'confirming'
  if (steps.some((step) => step.phase === 'submitted')) return 'submitted'
  return 'ready'
}
