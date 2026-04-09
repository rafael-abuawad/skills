---
name: react-avoid-unnecessary-effects
description: Guides React code away from unnecessary useEffect usage by preferring derived state, event handlers, keys, useMemo, and useSyncExternalStore. Use when writing or reviewing React components, hooks, data flow, performance, or when the user mentions useEffect, effects, or syncing state
---

# Avoid Unnecessary Effects (React)

Primary reference: [You Might Not Need an Effect](https://react.dev/learn/you-might-not-need-an-effect) (React docs).

## What Effects are for

`useEffect` is for **synchronizing with external systems**: non-React widgets, the browser DOM beyond React’s model, subscriptions that are not exposed as React state, or keeping UI in sync with **async external sources** (e.g. network) while a component is shown.

If nothing **outside** React is involved, you usually **do not** need an Effect.

## Do not use Effects for these (use the alternative)

| Situation | Prefer |
|-----------|--------|
| Derive UI from props/state (filter, map, concat, format) | Compute **during render**; avoid redundant state |
| Expensive pure derivation | `useMemo` (only when profiling shows cost) |
| User-driven logic (submit, click, navigation) | **Event handlers** (`onSubmit`, `onClick`, etc.) |
| Reset local state when a route/entity id changes | **`key`** on a child so state remounts cleanly |
| Adjust one piece of state when a prop changes | Prefer **derive during render** (e.g. store id, derive object); if unavoidable, React’s “adjust during render” pattern with previous-render guard—not an Effect chain |
| Notify parent of child state | Update parent in the **same event** as the child, or **lift state** |
| Child fetches then lifts data to parent via Effect | Parent **fetches** (or owns query) and **passes data down** |
| Browser/global subscription (`online`, `matchMedia`, etc.) | Prefer **`useSyncExternalStore`** over manual `useEffect` + listeners |

## Event vs “because it mounted”

- **Effect**: runs because the user **saw** the UI (e.g. analytics on view, keeping search results aligned with query+page while visible).
- **Event handler**: runs because the user **did** something specific (submit, buy, toggle).

Putting submit/network side effects only in Effects tied to state flags often causes bugs (e.g. wrong firing on initial state or remount).

## Chains of Effects

Avoid multiple Effects that only exist to `setState` in sequence. **Derive** what you can during render; compute **next state in the event handler** when the user acts. Effect chains cause extra renders and are hard to extend (e.g. time-travel, undo).

## Fetching in Effects (when you keep it)

If an Effect fetches based on inputs (`query`, `page`, `tokenId`):

- Add **cleanup** (`ignore` flag or `AbortController`) so stale responses do not win (race conditions).
- Prefer framework/data-library patterns when available; raw Effects are a last resort for orchestration.

## Initial “run once per app”

Avoid assuming a top-level `useEffect(..., [])` runs exactly once forever (Strict Mode remounts in dev). For true once-per-load logic, use module scope guards or app entry initialization—see the same doc section.

## Quick decision checklist

1. Is this **purely** a function of props/state? → Compute in render; no Effect.
2. Did the **user** cause it? → Event handler.
3. Must this subtree **reset** when `id` changes? → `key={id}` on inner component.
4. Subscribing to **external store**? → `useSyncExternalStore`.
5. Syncing with **network** while visible? → Effect + cleanup (or data library).

## When suggesting refactors

- Remove redundant state that mirrors props or other state.
- Move `setState` triggered by user actions from Effects into handlers.
- Replace listener Effects with `useSyncExternalStore` where applicable.
- Do not add Effects “to be safe” for derived UI—prefer simpler data flow.
