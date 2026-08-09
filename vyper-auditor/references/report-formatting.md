# Report Formatting

## Report path

Only with `--file-output`, save the report in the repository working directory as:

`{project-name}-pashov-ai-vyper-audit-report-{timestamp}.md`

`{project-name}` is the repository-root basename and `{timestamp}` is scan-time
`YYYYMMDD-HHMMSS`. Print the written path after the terminal report. Do not write
anything without the explicit flag.

## Output format

````markdown
# 🔐 Security Review — <ContractName or repository name> (Vyper)

---

## Scope

| | |
| --- | --- |
| **Mode** | default / filename |
| **Files reviewed** | `File1.vy` · `File2.vy`<br>`File3.vy` · `File4.vy` | <!-- list every file, 3 per line --> |
| **Compiler context** | <pragma(s), resolved deployment compiler if known, or `not verified`> |
| **Confidence threshold (1-100)** | 80 |

---

Completeness: N unique (contract, function) in raw, N covered in final.

## Findings

[95] **1. <Title>** [agents: 1, 6]

`ContractName.function_name` · Confidence: 95

**Description**
<The vulnerable Vyper code pattern and why it is exploitable, in one short sentence.>

**Proof**
<Concrete values, trace, and relevant source locations.>

**Fix**

```diff
- vulnerable line(s)
+ fixed line(s)
```

---

[82] **2. <Title>** [agents: 2]

`ContractName.__default__` · Confidence: 82

**Description**
<The vulnerable Vyper code pattern and why it is exploitable, in one short sentence.>

**Proof**
<Concrete values, trace, and relevant source locations.>

**Fix**

```diff
- vulnerable line(s)
+ fixed line(s)
```

---

[75] **3. <Title>** [agents: 4, 12]

`ContractName.function_name` · Confidence: 75

**Description**
<The vulnerable Vyper code pattern and why it is exploitable, in one short sentence.>

**Proof**
<Concrete values, trace, and relevant source locations.>

---

<All below-threshold findings have a description and proof, but no Fix block.>

---

## Findings list

| # | Confidence | Title |
| --- | --- | --- |
| 1 | [95] | <title> |
| 2 | [82] | <title> |
| | | **Below Confidence Threshold** |
| 3 | [75] | <title> |

---

## Leads

_Vulnerability trails with a concrete code smell where the full exploit path could
not be completed in this review. Leads are not false positives and are not scored._

- **<Title>** — `ContractName.function_name` — Code smells: <specific code smell> — Unverified: <the exact missing deployment fact, call path, or external behavior> — <one or two sentence trail>

---

> ⚠️ This review was performed by an AI assistant. AI analysis cannot verify the complete absence of vulnerabilities and no security guarantee is given. Team security reviews, bug-bounty programs, and on-chain monitoring are strongly recommended. For consultation, visit [https://www.pashov.com](https://www.pashov.com).
````

## Rules

- Follow the template exactly. Use Vyper snake_case function names and dunder names
  (`__init__`, `__default__`) where relevant.
- Sort findings by confidence descending and number sequentially. Findings below 80
  omit the **Fix** block, not their proof.
- Preserve `[agents: …]`, any `Chain: [A] + [B]` annotation, and every distinct
  safe fix option from deduplication.
- For version-sensitive findings, include the compiler evidence in **Proof**. If it
  is unverified, the item is normally a lead.
- Draft directly in this report format; do not first create an unstructured list and
  then regenerate it.
