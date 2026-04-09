---

## name: ai-first-ui-aesthetics
description: Designs distinctive AI-native interfaces—chat, agents, copilots, streaming responses, tool-call UIs, reasoning panels—by pairing A Color Bright’s AI visual-identity trends and brand archetypes with strong frontend craft. Use when building LLM UIs, AI dashboards, AI SDK surfaces, or when the user asks for aesthetics-of-AI, AI-first layout, or on-brand AI chrome. Apply at most one primary and one secondary trend consciously; avoid stacking many trends (sameness risk).

# AI-first UI aesthetics

## Quick start

Before implementing UI:

1. **Infer the product archetype** (one dominant tone). See “Archetype → UI tone.”
2. Pick **one primary** and **at most one secondary** visual trend from the report. Do **not** stack many trends on one surface— that produces undifferentiated “AI template” chrome.
3. **Commit to a direction** for typography, color, motion, and layout (see “Merge with frontend-design craft”).
4. Implement structure with **shadcn/ui** (or project equivalents); express art direction via **tokens, spacing, textures, motion**, not ad-hoc rainbow gradients.

For trend names and short definitions, see [reference.md](reference.md).

## Archetype → UI tone

Map positioning to interface character (from A Color Bright’s five clusters—names paraphrased):


| Archetype            | UI tone              | Typical cues                                                                                                                                                 |
| -------------------- | -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Likeable leaders** | Calm authority       | Muted warm neutrals, soft gradients or impressionistic hero art, rounded surfaces, human-leaning photography/illustration; **low friction**, no sharp edges. |
| **Gentle humanists** | People-first         | Hand-drawn or organic illustration accents, everyday warmth, generous whitespace; tech **recedes**—focus on outcomes and human scenes.                       |
| **Nerdy idealists**  | Lab culture          | Monospace accents, scribbles/diagram hints, playful rough edges, insider references; **peer-to-peer** energy—not glossy consumer polish.                     |
| **Bold builders**    | Transformative power | Darker bases, cosmic/scale motifs sparingly, confident contrast; ambition over “cozy”—still **legible** and accessible.                                      |
| **Utopian dreamers** | Imagined futures     | Surreal/retrofuturist **hero** moments; everyday chrome stays readable—reserve spectacle for onboarding/marketing, not dense tools.                          |


Brand examples in the source report are **illustrative**; do not pastiche a single competitor.

## Trend → UI patterns

Translate trends into **repeatable UI decisions** (not decoration dumps):

- **Off-white / organic gradients** — Layered backgrounds, warm neutrals in CSS variables, subtle grain or noise; gradients with **organic stops** and texture, not flat two-color defaults.
- **Digital impressionism / morphing / generative** — Streaming tokens, “thinking,” and idle states: soft pulses, diffuse blobs, emergent grids—**mood without literal “brain” diagrams**.
- **Sketch / scribble / technical illustration** — Connector lines, annotation callouts, lightweight diagram **frames** for tool steps or optional reasoning—only when it clarifies flow; avoid fake complexity.
- **ASCII / pixel / lomo** — Micro-moments: empty states, dev toggles, playful errors; **one accent family** per product, not every panel.
- **Contemporary realism / space / surrealism** — Marketing shells, hero sections, onboarding—**avoid** obscuring data-dense tools.

Full trend list: [reference.md](reference.md).

## Merge with frontend-design craft

- **Bold but intentional**: pick an extreme (e.g. refined minimal vs. expansive dream) that matches the archetype—**not** default purple-on-white “AI slop.”
- **Typography**: pair a distinctive display with a readable body face; avoid lazy Inter/Roboto-only stacks unless the design system already owns that choice with strong art direction elsewhere.
- **Motion**: one **orchestrated** beat (e.g. staggered reveal on first paint) outperforms scattered micro-noise; respect `prefers-reduced-motion`.
- **Accessibility**: contrast, focus rings, and screen-reader semantics are mandatory—even for soft, dreamy palettes.

## Implementation hooks (shadcn)

Prefer composing **shadcn/ui** primitives for AI surfaces:

- **Chat / feed:** `ScrollArea`, `Card`, `Skeleton` for streaming; `Tooltip` for token/tool metadata.
- **Overlays:** `Dialog`, `Sheet`, `Drawer` for tool details, settings, side panels.
- **Inputs:** `Textarea`, `Button`, command palettes or custom prompt bars styled via tokens—not one-off inline styles scattered everywhere.

Centralize **colors, radii, fonts** in theme tokens; use layout (grid, asymmetry, overlap) to differentiate—not only hue shifts.

## Anti-patterns

- Clichéd **purple gradient on white** with no product-specific story.
- **Every** card and panel using gradients; no resting neutral plane.
- **Trend soup**: mascot + space + pixel + academia + surreal hero in one view.
- **Hiding weak UX** behind flashy “AI aesthetics.”
- **Copying** one known AI brand’s look pixel-adjacent (fails differentiation per the report).

## Attribution

Insights on trends and archetypes are synthesized from **A Color Bright**, *Aesthetics of AI* — [acolorbright.com/insight](https://acolorbright.com/insight). Industry evolves quickly; treat the report as **strategic vocabulary**, not a fixed style guide.