---
name: modern-front-end-design
description: Creates distinctive, production-grade modern frontend interfaces with intentional art direction, clean implementation, responsive behavior, accessibility, and rigorous visual verification. Use only when explicitly invoked for frontend components, pages, applications, redesigns, or design-system work.
disable-model-invocation: true
---

# Modern Front-End Design

Build memorable interfaces that are useful, maintainable, and visually precise. Treat design as a system of deliberate choices, not decoration.

## Operating principles

1. Verify the request and the existing product before accepting assumptions.
2. Preserve established project conventions unless the task explicitly calls for a redesign.
3. Choose one clear visual concept and execute it consistently.
4. Prefer a small number of strong decisions over many weak effects.
5. Match implementation complexity to the design: refined minimalism needs precision; expressive work may justify richer motion and layering.
6. Keep the requested scope narrow. Ask before adding unrelated enhancements, dependencies, pages, or product features.
7. Build real interactions and states. Do not ship a static mockup when working functionality is expected.

## Design workflow

### 1. Understand the interface

Determine:

- Purpose: what job the interface performs.
- Audience: who uses it and under what conditions.
- Hierarchy: the primary action, secondary actions, and supporting information.
- Constraints: framework, component library, browser support, accessibility, performance, and existing design tokens.
- States: loading, empty, error, success, disabled, validation, and overflow cases.

Inspect the current code and rendered interface when available. Do not invent a new visual language without understanding the existing one.

### 2. Declare the art direction

Before implementation, form a concise internal design brief:

```text
Concept: [specific aesthetic direction]
Memorable device: [the one visual or interaction idea users will remember]
Typography: [display and body strategy]
Palette: [dominant, supporting, and accent colors]
Composition: [grid, asymmetry, density, and responsive behavior]
Motion: [one coordinated motion idea and reduced-motion behavior]
```

Choose a direction appropriate to the product, such as editorial, industrial, art deco, retro-futurist, organic, playful, luxury, brutalist, or restrained minimalism. Do not combine unrelated aesthetics.

### 3. Establish the visual system

Define reusable tokens for:

- Color roles, including surface, text, border, accent, success, warning, and danger.
- Type scale, line height, letter spacing, and measure.
- Spacing rhythm and layout widths.
- Border radius, border weight, elevation, and focus treatment.
- Motion duration, easing, and stagger.

Use CSS variables or the project's token system. Maintain readable contrast and visible focus states.

### 4. Implement the complete slice

- Use semantic HTML and the project's framework conventions.
- Reuse existing components and tokens before creating new primitives.
- For React projects without another component library, use shadcn/ui primitives and customize them to the chosen art direction.
- Keep components focused and composable; separate data behavior from presentation where useful.
- Use strict types. Avoid unsafe casts and `any`.
- Make layouts responsive from narrow mobile screens through wide desktops.
- Account for long text, missing media, dense data, and keyboard navigation.
- Use optimized images, intentional aspect ratios, and stable dimensions.
- Add motion only when it improves hierarchy, feedback, or spatial understanding.
- Respect `prefers-reduced-motion`.

## Aesthetic standards

### Typography

- Select characterful fonts that fit the concept; pair a distinctive display face with a highly readable body face when appropriate.
- Avoid defaulting to Arial, Inter, Roboto, generic system stacks, or repeatedly using the same fashionable font.
- Use weight, scale, line length, and spacing to create hierarchy rather than excessive color.
- Provide resilient fallbacks and avoid unnecessary font payload.

### Color

- Commit to a dominant palette with a controlled accent.
- Avoid cliché purple-on-white gradients and timid, evenly distributed color.
- Check text, icon, border, focus, hover, and disabled contrast.
- Use gradients, transparency, and glow only when they reinforce the concept.

### Composition

- Use intentional negative space or controlled density.
- Consider asymmetry, overlap, cropping, vertical rhythm, and grid-breaking moments.
- Keep unconventional layouts understandable and operable.
- Avoid predictable stacks of centered hero copy, generic cards, and evenly spaced feature grids unless the product genuinely calls for them.

### Depth and detail

- Create atmosphere through restrained texture, grain, pattern, layering, illustration, or shadow.
- Make decorative details context-specific rather than ornamental filler.
- Keep visual effects from reducing readability or performance.

### Motion

- Prefer one coordinated entrance or transition system over unrelated animations.
- Use hover and press states to communicate affordance.
- Animate opacity and transforms where possible.
- Avoid blocking interaction, excessive parallax, and constant ambient movement.

## Anti-patterns

Do not:

- Produce generic “AI dashboard” or template-marketplace aesthetics.
- Add random gradients, glass panels, oversized rounded cards, or floating blobs without conceptual purpose.
- Hide weak hierarchy behind animation.
- Replace clear labels with ambiguous icons.
- Sacrifice accessibility for novelty.
- Create bespoke buttons, inputs, dialogs, or menus when the project already has suitable primitives.
- Add dependencies for effects achievable cleanly with existing tools or CSS.
- Rewrite unrelated code while implementing a visual change.

## Verification loop

After implementation:

1. Run formatting, linting, type checks, and relevant tests.
2. Render the interface at mobile and desktop widths.
3. Exercise primary interactions and all requested states.
4. Check keyboard navigation, focus order, labels, contrast, and reduced motion.
5. Look for clipping, overflow, layout shift, hydration errors, and console errors.
6. Compare the result against the declared concept and remove anything inconsistent.
7. Repeat until checks pass and the rendered result is coherent.

Do not claim visual quality from code inspection alone when a rendered preview can be tested.

## Delivery

Report:

- The implemented design direction in one sentence.
- The main functional and visual changes.
- Verification performed and any limitations.
- Optional enhancements separately; ask before implementing them.
