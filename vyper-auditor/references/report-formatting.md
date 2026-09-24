# Report and run-file contract

`assemble.sh` produces the report; `scripts/scan.py terminal` selects terminal
output and makes an optional copy. The orchestrator writes run blocks, not a
second report. The threshold comes from `judging.md`.

## Run files

Each completed pass writes `run-K.md` beginning with:

```markdown
<!--RUN pass=1 agents=12/12-->

Completeness: 2 unique (file, function) in raw, 2 covered in final, 0 rejected with reasons.
```

If agents fail, state their specialties immediately after the header. Write the
same successful agent count to `pass_K_agents` in scope. Gates and rejected paths
may be documented in this preamble, outside finding blocks.

Use exactly these block layouts; the blank lines are part of the parser contract.
Titles have no leading sequence number. The assembler numbers the final findings.

````markdown
<!--F key=src-vault-vy|withdraw|unchecked-transfer conf=95 kind=FINDING agents=1,6-->

[95] **The vault ignores failed transfers**

`src/vault.vy.withdraw` · Confidence: 95

**Description**
A token can reject the transfer while the vault removes the user's shares.

**Proof**
Concrete source locations, values, and a state/call trace. Include compiler
configuration evidence whenever the claim depends on the compiler version.

**Fix**

```diff
- extcall IERC20(token).transfer(receiver, amount)
+ assert extcall IERC20(token).transfer(receiver, amount)
```

<!--/F-->

<!--F key=src-vault-vy|deposit|token-behavior kind=LEAD agents=3-->

- **The vault may overcredit deposits** — `src/vault.vy.deposit` — Code smells: accounting uses the requested amount — Unverified: whether the accepted token deducts transfer fees.

<!--/F-->
````

A finding always has Description and Proof. Below threshold, omit Fix. Also omit
Fix for the explicit partial-path promotion exception; explain the unverified link
in Proof. Preserve alternative fixes as separately labelled diff blocks. Fixes are
verified suggestions, never applied to the audited source.

Each marker carries a normalized file|function|bug-class key. FINDING has an
integer confidence 1–100; LEAD has no confidence attribute. `agents` is a comma-
separated list of specialty numbers 1–12. The location retains source spelling
and must normalize to the key's first two segments. Tabs are forbidden in titles,
locations, and single-line leads; code/proof bodies may retain their formatting.
Markers are whole lines outside code fences. See [scan-state.md](scan-state.md)
for exact normalization and module/export attribution.

## Assembled report

The title is `Security Review — {project-name} (Vyper)`. Sections are Scope,
Findings, Findings List (unless empty), Leads, optionally Known from earlier scans,
and the disclaimer. Findings sort by confidence descending; all proofs and fix
bodies are copied through without rewriting. Agent attribution stays visible.

A plain Scope table contains Mode, Files reviewed, Compiler context, and Confidence
threshold. It has no Passes or Memory row. A multi-pass scan adds planned/completed
passes and failures. Memory adds the post-prune before count, after count, and frozen
SHA. Missing/broken run records or lost coverage produce a warning even on one pass.
A memory write failure also appears in Scope; it must not imply persistence succeeded.

`scope.tsv` is append-only key<TAB>value, last line wins. `files` is a JSON array
of complete paths, wrapped three per display line. Other values contain no literal
tabs/newlines. The helper writes scan facts; the orchestrator appends compiler
context, `pass_K_agents`, `pass_K_failed`, and errors as observed.

Across runs, one write-up survives per key: FINDING before LEAD, then highest
confidence, then later pass. Confidence is not increased by repetition. Preserve
distinct mechanisms within each pass before this deterministic selection.
`seen in k/N runs` counts unique run files raising the key and appears only when
more than one run file exists. `KNOWN (n scans)` means present before this scan,
with the stored count plus one; otherwise NEW. Memory labels appear only with
memory enabled. Old records not raised again appear as explicitly not re-checked.

Empty findings/leads are stated in words. No run file means “This scan reviewed
nothing”; surviving agents that found nothing remain a valid completed run.

## Output paths and size

Every scan assembles `.vyper-auditor/runs/{stamp}/full-report.md`. With
`--file-output`, copy those bytes to
`{project-name}-pashov-ai-vyper-audit-report-{stamp}.md` in the audited root.

At most 20 findings: print the report in full. More than 20: print scope unchanged,
`Findings List — top 3 of F`, three mechanically extracted rows, one full-report
path, and the disclaimer. Use the copy path when requested, otherwise the internal
path. Leads do not trigger abbreviation. No unlabeled truncation, rewritten
finding bodies, or confidence-bucket summaries.
