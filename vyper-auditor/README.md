# Vyper Auditor

A security agent with a simple mission — findings in minutes, not weeks.

Built for:

- **Vyper devs** who want a security check before every commit
- **Security researchers** looking for fast wins before a manual review
- **Anyone** who wants an extra pair of eyes on `.vy` contracts.

Not a substitute for a formal audit — but the check you should never skip.

## Demo

_Portrayed below: finding multiple high-confidence vulnerabilities in a codebase (Solidity demo; workflow is the same for Vyper.)_

![Running auditor skill in terminal](../static/skill_pag.gif)

## Usage

```bash
# Scan the full repo (default)
/vyper-auditor

# Full repo + adversarial reasoning agent (slower, more thorough)
/vyper-auditor deep

# Review specific file(s)
/vyper-auditor src/Tokenizer.vy
/vyper-auditor src/Tokenizer.vy src/Other.vy

# Write report to a markdown file (terminal-only by default)
/vyper-auditor --file-output
```

## Known Limitations

**Codebase size.** Works best up to ~2,500 lines of Vyper. Past ~5,000 lines, triage accuracy and mid-bundle recall drop noticeably. For large codebases, run per module rather than everything at once.

**What AI misses.** AI is strong at pattern matching — missing access controls, unchecked return values, known reentrancy shapes. It struggles with relational reasoning: multi-transaction state setups, specification/invariant bugs, cross-protocol composability, game-theory attacks, and off-chain assumptions. AI catches what humans forget to check. Humans catch what AI cannot reason about. You need both.
