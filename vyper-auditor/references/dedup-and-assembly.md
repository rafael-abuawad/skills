# Deduplicate, record, and assemble

Read once while the first pass runs. Turn 4 repeats per pass; Turn 5 runs once.
Use the frozen source, shared rules, judging rules, and Vyper semantics throughout.

## Turn 4 — Deduplicate, validate, record

1. **Deduplicate within a file and function.** Group exact keys first. Canonicalize
   synonymous bug classes only when they name the same defect: reuse the known
   label, otherwise the most frequent label, otherwise the shortest defect label.
   Distinct bugs keep distinct labels. Never merge different files or functions.
   For a shared group, preserve every mechanism, attack path, and distinct fix.
   Repeat the comparison within each file/function across bug-class boundaries;
   every distinct raw mechanism must survive in a final candidate.

   Collect the raw fixes. Different called expressions, check directions, or
   checked parameters require separate labelled `Fix (Option A — …)` diff blocks.
   Keep the selected code verbatim after safety verification; do not synthesize
   a new fix by mixing alternatives. Refuted or unsafe alternatives are not fixes;
   explain their exclusion in the pass working notes.

   Account for every raw file/function tuple as a finding, lead, or explicit
   gate rejection. Record `Completeness: N unique (file, function) in raw,
   M covered in final, R rejected with reasons.` in the run preamble. Never rescue
   a rejected issue merely to satisfy coverage accounting. If A enables B and the
   combined harm exceeds either alone, preserve a chain explanation at confidence
   min(A, B), using stable locations/keys rather than temporary report numbers.

2. **Gate once.** Apply all four gates in `judging.md` in order. For relevant
   paths use `__init__` → setters → deposit/swap → mint → burn/withdraw →
   liquidation → `__default__`. Record BLOCKS, ALLOWS, IRRELEVANT, or UNCERTAIN;
   treat uncertainty as non-refutation, never as proof of a compiler version.
   Commit the verdict; do not repeatedly reopen a completed gate.

3. **Promote or reject** using all three judging rules, including the partial-path
   exception at 75 with no Fix block. Multi-agent agreement never defeats a
   concrete guard or missing compiler-version evidence. Preserve proof for all
   findings; clearly identify the missing link in partial-path promotions.

4. **Verify fixes** for findings at/above the threshold, except the documented
   partial-path exception. Trace the attack with the fix and check for new DoS,
   reentrancy, or invariant failures. Preserve asserted `extcall` return values,
   deliberate no-return-token support, code-existence checks, and fully validated
   `raw_call` responses. Enumerate repeated locations. If no safe minimal fix is
   available, say so; do not provide unsafe code.

5. **Write `run-K.md`** in the run directory using [report-formatting.md](report-formatting.md).
   Keys are required even when memory is off because the assembler indexes them.
   Normalize once; the run blocks supply the ledger as well as the report.
   Reuse the same bug labels supplied in known findings. Write full Description,
   Proof, and safe Fix blocks now, following [report-language.md](report-language.md)
   for prose without changing identifiers, labels, evidence, or code.

   Start with `<!--RUN pass=K agents=C/12-->`, then name failed specialties and
   coverage accounting in prose. Append `pass_K_agents<TAB>C/12` to `scope.tsv`,
   including `12/12`. A pass with surviving agents but no findings still writes a
   run header; it is not the same as a pass with no surviving agents.

6. **Merge only when memory is on:**

   ```bash
   python3 "{helper}" merge --bundle "{bundle_dir}" --pass {K}
   ```

   It preserves one scan increment across all passes, updates scope counts, and
   prints the multi-pass progress line. Counts mean gated findings/leads, “new”
   means absent before this pass, and `no new ground` means both new counts are
   zero. One-pass memory prints no summary. Merge failure stops the loop: retain
   completed files, append `memory_error<TAB>{sanitized error}` to scope, and
   attempt Turn 5 so readable findings remain available. Do not retry with a
   fresh ledger or advertise successful persistence.

No report is printed inside the loop. The next pass rebuilds known findings and
bundles only after every previous-pass agent is finished.

## Turn 5 — Assemble, print, clean

1. Run the sole report producer:

   ```bash
   bash "{resolved_path}/assemble.sh" --dir "{run_directory}"
   ```

   It consumes scope, run blocks, and the memory snapshot/name map when enabled.
   It writes a `.part` file then renames it to `full-report.md`. Broken blocks and
   lost agents produce visible coverage warnings; all readable findings survive.
   If assembly exits nonzero, print the error, clean the bundle, and stop. Do not
   hand-compose a replacement report.

2. Extract terminal output mechanically:

   ```bash
   python3 "{helper}" terminal --dir "{run_directory}"
   ```

   Add `--file-output` only when requested. The helper makes the byte-identical
   Vyper-named copy before printing its path. At ≤20 findings it prints the full
   report. At >20 it prints unchanged scope, the top three rows with the total,
   one report path, and the disclaimer. Leads do not count toward the limit.
   Seen appears only on multi-pass tables. If count validation disagrees, warn
   and print in full. Pass the output through without rewriting it.

3. Remove this scan's `{bundle_dir}` only, including after failures. Preserve
   `.vyper-auditor/runs/{stamp}/` and the last complete ledger. Never sweep other
   bundles, clean between passes, or write audit PoCs in the repository.
