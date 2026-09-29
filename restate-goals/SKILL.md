---
name: restate-goals
description: Restates, in the agent's own words, what it thinks the user's goals are and what problem the user is trying to solve, then waits before acting. Use when the user invokes restate-goals, asks to restate goals, confirm understanding, or align on the problem before work begins.
disable-model-invocation: true
---

# Restate goals

Before any other work, restate in your own words what you think my goals are and what the problem i'm trying to solve is.

## How to restate

Write two short parts, in this order:

1. **Goals** — what you think the user is trying to achieve.
2. **Problem** — what problem you think they are trying to solve.

Use your own words. Do not quote the request back, paraphrase it lightly, or list the steps you plan to take.

If a goal or the problem is ambiguous, name the assumption in the same restatement.

## Stop

End the turn after the restatement. Do not edit files, run commands, or start the task in that turn.

Continue only after the user confirms the restatement or corrects it. If they correct it, restate the updated goals and problem in your own words and stop again.
