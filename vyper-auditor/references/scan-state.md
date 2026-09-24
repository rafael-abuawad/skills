# Scan state and Vyper identities

`scripts/scan.py` is the standard-library implementation of discovery, source
identity, ledger validation/pruning, known findings, and atomic merges. Use its
commands from SKILL.md; do not reproduce these operations in model-written awk.
Bash `find` still discovers files and `references/assemble.sh` produces reports.

## Identities

The `contract` field is the repository-relative path including `.vy`, not a class
name or basename. `function` is the defining source identifier, a public getter's
variable name, or `__module__` for a file-level defect. For exported function code,
use its defining module; for host wiring/export defects use the host. Preserve
host context in the proof. Named files outside the root retain their `../` prefix.

Normalize **each** of path, function, and bug class separately: lowercase, replace
every run of non-ASCII-alphanumeric characters with one hyphen. Do not strip the
resulting hyphens. Join the three segments with `|`. For example:

`src/Vault.vy | __init__ | missing-owner-check`
→ `src-vault-vy|-init-|missing-owner-check`.

The frozen source index rejects path collisions and per-file function collisions
instead of merging unrelated identities. Bug labels are canonicalized during
deduplication, before key creation. Original source spellings remain in reports.
`source-names.tsv` maps normalized `file|function` pairs to original
`path.vy.function` locations. A function in one file never keeps another file's
removed function alive. Unmapped records on a named-file scan display stored keys.

The lexer includes `def` declarations (including dunder functions), multiline
`public(...)` declarations, and `__module__`. Strings/comments are not declarations.
Files with exports or tokenization uncertainty retain unmatched function records.
This conservative rule avoids claiming that an unresolved module route disappeared.
No compiler installation or untrusted project code is executed for indexing.

## Memory lifecycle

Memory is enabled by `--memory` or passes > 1. A plain scan never reads, validates,
prunes, or writes a ledger, even if an invalid ledger already exists.

The first header field is `#vyper-auditor-memory v1`; data rows have six fields:

`key<TAB>status<TAB>scans<TAB>sha<TAB>title<TAB>kind`

Validate header, field count, unique well-formed keys, status (`NEW`/`KNOWN`),
positive scan count, and kind (`FINDING`/`LEAD`) before any agents. Invalid input
stops the scan without overwriting it. A stale `.tmp` is warned about and replaced
on the next successful merge; it is never treated as the ledger.

Preparation snapshots the ledger. In default mode only, prune records whose file
is absent or whose function is demonstrably absent from that file. Print every
pruned key, kind, and title. Never prune a named-file scan. The prune changes only
the snapshot; the live ledger inherits it after the first successful pass. Record
`mem_before` once from the post-prune snapshot, including zero for an empty ledger.

After each pass, `merge --bundle ... --pass K` reads the validated run blocks from
all completed passes. Those blocks are also the assembler's input: there is no
second model-written row list. Rebuild from the pre-scan snapshot each time:

- Re-found old key: `KNOWN`, previous scans + 1, current SHA/title/kind.
- Old key not re-found: unchanged.
- New key: `NEW`, scans 1.

Repeated keys take the last pass's ledger metadata. Kind is not part of the key;
LEAD ↔ FINDING changes the record in place. Report selection independently favors
FINDING over LEAD, then confidence, then later pass. Repetition never raises
confidence. Repeating a merge is idempotent. The SHA is captured once when source
is frozen; outside Git or before the first commit it is `none`.

Write `memory.tsv.tmp` completely, then replace `memory.tsv` on the same filesystem.
Malformed run blocks abort the merge and preserve the previous ledger. `mem_after`
and `mem_sha` scope keys describe the latest successful merge. The run directory
already holds the pre-scan snapshot and name map, so bundle cleanup cannot remove
report inputs. Do not run two memory-enabled scans against the same repo at once;
there is no shared-writer merge protocol.

The next pass's known-findings file comes from the live merged ledger. Tags in
reports always use the pre-scan snapshot: a bug first found in pass 1 remains NEW
in pass 3. Known records not raised this scan are explicitly **not re-checked**,
not presumed fixed or still open.
