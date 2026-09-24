# Five property-discovery perspectives

Input to every perspective: protocol understanding, relevant docs, in-scope Vyper source and ABI, actor/deployment setup, actions, model state, and existing properties. Give source paths and contract/function scope. Discovery is read-only; return proposals to one synthesizer rather than editing shared files.

Apply all five perspectives. Use independent agents when available within the host concurrency limit, inheriting its configured model; schedule waves when slots are limited. Otherwise execute the perspectives sequentially and distinguish their findings.

1. **Conservation:** For each aggregate, identify independently enumerable parts and external value flows. Propose balance/asset/liability identities, conservation bounds, and solvency checks. Include fees, donations, accrued interest, and rounding assumptions.
2. **Round trips and rounding:** Identify inverse operation pairs, conversions, previews, and decimal domains. Derive directional inequalities and tolerances from implementation/spec evidence. Avoid claiming exact equality when fees or rounding apply.
3. **State transitions:** Map entity lifecycle states, roles, deadlines, counters, and monotonic quantities. Propose operation postconditions, forbidden transitions, and rejected-call non-mutation checks. Identify necessary setup/actions to reach each state.
4. **Adversarial behavior:** Explore unauthorized actions, sequence dependence, replay/double-use, dust, empty/full states, liveness, and value extraction. State attacker resources and environmental assumptions; distinguish a profitable trace from a mere unexpected revert.
5. **Protocol-specific guarantees:** Identify the protocol family (vault, lending, AMM, staking, governance, bridge, or other). Propose guarantees grounded in its actual implementation and documented design, rather than applying a template indiscriminately.

Return for each proposal: short name, global/postcondition kind, precise predicate with units, priority, SHOULD-HOLD/EXPLORATORY classification and evidence, assumptions, source/function dependencies, required ghost state and snapshots, reachability prerequisites, and possible false positives. Report uncertainty instead of inventing guarantees.

The synthesizer deduplicates overlapping proposals, reconciles conflicting assumptions against evidence, assigns stable `GL-NN`/`SP-NN` identifiers, and writes the property plan and spec using [the property contract](../references/properties.md). Prefer independently meaningful checks over a large property count. A single integrating writer implements the accepted plan and reconciles shared model state.
