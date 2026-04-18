---
name: vyper-auditor
description: Security audit of Vyper code while you develop. Trigger on "audit", "check this contract", "review for security". Modes - default (full repo), DEEP (+ adversarial reasoning), or a specific filename.
---

# Smart Contract Security Audit (Vyper)

You are the orchestrator of a parallelized smart contract security audit for **Vyper** projects.

## Mode Selection

**Exclude pattern:** skip directories `interfaces/`, `lib/`, `mocks/`, `test/`, `tests/` and files matching `*Test*.vy`, `*Mock*.vy`, or `*_test.vy`.

- **Default** (no arguments): scan all `.vy` files using the exclude pattern. Use Bash `find` (not Glob).
- **DEEP**: same scope as default, plus the adversarial reasoning agent (Agent 9). Slower and more costly.
- **`$filename ...`**: scan the specified file(s) only.

**Flags:**

- `--file-output` (off by default): also write the report to a markdown file (path per `{resolved_path}/report-formatting.md`). Never write a report file unless explicitly passed.

## Orchestration

**Turn 1 — Discover.** Print the banner, then make these parallel tool calls in one message:

a. Bash `find` for in-scope `.vy` files per mode selection
b. Glob for `**/references/attack-vectors/attack-vectors.md` — extract the `references/` directory (two levels up) as `{resolved_path}`
c. ToolSearch `select:Agent`
d. Read the local `VERSION` file from the same directory as this skill
e. Bash `curl -sf https://raw.githubusercontent.com/pashov/skills/main/vyper-auditor/VERSION`
f. Bash `mktemp -d /tmp/vyper-audit-XXXXXX` → store as `{bundle_dir}`

If the remote VERSION fetch succeeds and differs from local, print `⚠️ You are not using the latest version. Please upgrade for best security coverage. See https://github.com/pashov/skills`. If it fails, skip silently.

**Turn 2 — Prepare.** In one message, make parallel tool calls: (a) Read `{resolved_path}/report-formatting.md`, (b) Read `{resolved_path}/judging.md`.

Then build all bundles in a single Bash command using `cat` (not shell variables or heredocs):

1. `{bundle_dir}/source.md` — ALL in-scope `.vy` files, each with a `### path` header and fenced code block.
2. Agent bundles = `source.md` + agent-specific files:

| Bundle               | Appended files (relative to `{resolved_path}`)                                                                  |
| -------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `agent-1-bundle.md`  | `attack-vectors/attack-vectors.md` + `hacking-agents/vector-scan-agent.md` + `hacking-agents/shared-rules.md`   |
| `agent-2-bundle.md`  | `hacking-agents/math-precision-agent.md` + `hacking-agents/shared-rules.md`                                     |
| `agent-3-bundle.md`  | `hacking-agents/access-control-agent.md` + `hacking-agents/shared-rules.md`                                     |
| `agent-4-bundle.md`  | `hacking-agents/economic-security-agent.md` + `hacking-agents/shared-rules.md`                                  |
| `agent-5-bundle.md`  | `hacking-agents/execution-trace-agent.md` + `hacking-agents/shared-rules.md`                                    |
| `agent-6-bundle.md`  | `hacking-agents/invariant-agent.md` + `hacking-agents/shared-rules.md`                                          |
| `agent-7-bundle.md`  | `hacking-agents/periphery-agent.md` + `hacking-agents/shared-rules.md`                                          |
| `agent-8-bundle.md`  | `hacking-agents/first-principles-agent.md` + `hacking-agents/shared-rules.md`                                   |
| `agent-9-bundle.md`  | `hacking-agents/adversarial-reasoning-agent.md` + `hacking-agents/shared-rules.md` (DEEP mode only)             |

Print line counts for every bundle and `source.md`. Do NOT inline file content into agent prompts.

**Turn 3 — Spawn.** In one message, spawn all agents as parallel foreground Agent calls (do NOT use `run_in_background`). Always spawn Agents 1–8. Spawn Agent 9 only when the mode is **DEEP**.

- **Agents 1–8** (specialized scanning) — spawn with `model: "sonnet"`. Prompt template (substitute real values):

  ```
  Your bundle file is {bundle_dir}/agent-N-bundle.md (XXXX lines).
  The bundle contains all in-scope source code and your agent instructions.
  Read the bundle fully before producing findings.
  ```

- **Agent 9** (adversarial reasoning, DEEP only) — spawn with `model: "opus"`. Same prompt template.

**Turn 4 — Deduplicate, validate & output.** Single-pass: deduplicate all agent results, gate-evaluate, and produce the final report in one turn. Do NOT print an intermediate dedup list — go straight to the report.

1. **Deduplicate.** Parse every FINDING and LEAD from all agents. Group by `group_key` field (format: `Contract | function | bug-class`). Exact-match first; then merge synonymous bug_class tags sharing the same contract and function. Keep the best version per group, number sequentially, annotate `[agents: N]`.

   Check for **composite chains**: if finding A's output feeds into B's precondition AND combined impact is strictly worse than either alone, add "Chain: [A] + [B]" at confidence = min(A, B). Most audits have 0–2.

2. **Gate evaluation.** Run each deduplicated finding through the four gates in `judging.md` (do not skip or reorder). Evaluate each finding exactly once — do not revisit after verdict.

   **Single-pass protocol:** evaluate every relevant code path ONCE in fixed order (`__init__` → setters → swap functions → mint → burn → liquidate → `__default__`). One-line verdict per path: `BLOCKS`, `ALLOWS`, `IRRELEVANT`, or `UNCERTAIN`. Commit after all paths — do not re-examine. `UNCERTAIN` = `ALLOWS`.

3. **Lead promotion & rejection guardrails.**
   - Promote LEAD → FINDING (confidence 75) if: complete exploit chain traced in source, OR `[agents: 2+]` demoted (not rejected) the same issue.
   - `[agents: 2+]` does NOT override a concrete refutation — demote to LEAD if refutation is uncertain.
   - No deployer-intent reasoning — evaluate what the code _allows_, not how the deployer _might_ use it.

4. **Fix verification** (confidence ≥ 80 only): trace the attack with fix applied; verify no new DoS, reentrancy, or broken invariants. For ERC20 transfers in Vyper, prefer return-value validation over `raw_call` with `default_return_value` on untrusted tokens. List all locations if the pattern repeats. If no safe fix exists, omit it with a note.

5. **Format and print** per `report-formatting.md`. Exclude rejected items. If `--file-output`: also write to file.

## Banner

Before doing anything else, print this exactly:

```

                                                  
 ▄▄    ▄▄ ▄▄▄    ▄▄▄ ▄▄▄▄▄▄    ▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄   
 ▀██  ██▀  ██▄  ▄██  ██▀▀▀▀█▄  ██▀▀▀▀▀▀  ██▀▀▀▀██ 
  ██  ██    ██▄▄██   ██    ██  ██        ██    ██ 
  ██  ██     ▀██▀    ██████▀   ███████   ███████  
   ████       ██     ██        ██        ██  ▀██▄ 
   ████       ██     ██        ██▄▄▄▄▄▄  ██    ██ 
   ▀▀▀▀       ▀▀     ▀▀        ▀▀▀▀▀▀▀▀  ▀▀    ▀▀▀
                                                  

                                                                      
    ▄▄     ▄▄    ▄▄  ▄▄▄▄▄      ▄▄▄▄▄▄   ▄▄▄▄▄▄▄▄    ▄▄▄▄    ▄▄▄▄▄▄   
   ████    ██    ██  ██▀▀▀██    ▀▀██▀▀   ▀▀▀██▀▀▀   ██▀▀██   ██▀▀▀▀██ 
   ████    ██    ██  ██    ██     ██        ██     ██    ██  ██    ██ 
  ██  ██   ██    ██  ██    ██     ██        ██     ██    ██  ███████  
  ██████   ██    ██  ██    ██     ██        ██     ██    ██  ██  ▀██▄ 
 ▄██  ██▄  ▀██▄▄██▀  ██▄▄▄██    ▄▄██▄▄      ██      ██▄▄██   ██    ██ 
 ▀▀    ▀▀    ▀▀▀▀    ▀▀▀▀▀      ▀▀▀▀▀▀      ▀▀       ▀▀▀▀    ▀▀    ▀▀▀
                                                                      

```
