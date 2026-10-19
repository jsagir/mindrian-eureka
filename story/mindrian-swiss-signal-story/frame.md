---
canvas:
  width: 1920
  height: 1080
palette:
  paper: '#F7F5EE'
  ink: '#111111'
  evidence_blue: '#1F3FBF'
  signal_red: '#D6281F'
  tension_yellow: '#F2C200'
  muted_ink: '#4B4943'
  soft_rule: '#C9C6BC'
typography:
  display: 'Figtree, Arial, sans-serif'
  reading: 'DM Sans, Arial, sans-serif'
  evidence: 'JetBrains Mono, monospace'
spacing:
  outer_x: 104
  outer_y: 70
  safe_bottom: 184
  column_gap: 52
  unit: 8
rules:
  corner_radius: 0
  rule_weight: 2
  heavy_rule_weight: 5
  shadow: none
  gradient: none
---

# Swiss Signal frame contract

Use a warm-paper editorial canvas with hard ink rules, flat color, and generous negative space. The frame should read like an investigative publication brought to life, not a dashboard or generic product interface.

## Typography

- Display: Figtree 900, 72–116px, tight tracking, short lines.
- Supporting copy: DM Sans 500–700, 28–40px, never smaller than 26px in-frame.
- Evidence labels and provenance: JetBrains Mono 600, 18–24px, uppercase.
- Keep visible wording sparse. Narration carries the full explanation; the frame carries the evidence state, relationship, and decision.

## Layout

- Use a consistent editorial shell: masthead at top, chapter marker at upper-left, main reasoning field through the center, Theo at right or integrated into the map, and status/provenance above the bottom safe area.
- Keep the lower 184px clear of essential content even though captions are disabled for this cut.
- Use asymmetry with one dominant focal relationship. Avoid evenly weighted card grids.
- Corners are square. No pills, glass, glow, shadows, gradients, floating panels, or rounded SaaS cards.

## Evidence grammar

- Blue, solid line: observed or established.
- Red, solid or struck line: assumption, conflict, or disconfirming result.
- Yellow marker: unresolved question, uncertainty, or decision point.
- Muted ink and dotted line: proposed relationship or historical model.
- Every abstraction must retain a visible route back to a source identifier.
- All case details are explicitly labelled ILLUSTRATIVE; never imply they are verified room findings.

## Theo

Theo is the eye-and-bar geometry from `assets/theo-face-rest.svg`, adapted into the six poses in `THEO-FACE-NOTE.md`. Theo is the guide between scales: eyes focus and redirect attention; the bar becomes an underline, connector, branch, or handoff outline. Do not place a separate mascot beside an unrelated diagram—the diagram should grow from Theo's geometry.

## Persistent visual spine

The blue underline beneath source E-17 becomes Theo's bar, then the opportunity-system connector, then the evidence timeline, then the portfolio dependency line. Preserve its approximate screen direction across scene boundaries so zooming out and back in feels like one continuous act of reasoning.

## Motion

- Editorial energy: deliberate, precise, calm. Use meaningful motion throughout each scene rather than settling in the first second.
- Eyes shift in about 220ms; Theo posture changes in about 380ms; evidence reframes in about 450ms.
- Primary transition is a restrained 0.45–0.65s crossfade. Use a focus-pull or viewport change only when moving between concrete and abstract levels.
- Draw paths with SVG stroke animation or scaleX from a correct transform origin. Never morph arbitrary SVG paths.
- Honor reduced motion by presenting the final legible state without essential information loss.

## Concrete illustrative thread

Use one coherent example throughout: a lab note observes that readings shift after the same sample is removed and replaced. The opportunity hypothesis is that positioning—not the sample itself—may drive the variation. Candidate responses include a self-registering holder, an alignment insert, and a calibration protocol. The consequential test compares repeated reseating with and without the insert. Keep the observation, hypothesis, opportunity branches, and result explicitly marked illustrative.

## Bans

- No generated hero imagery, photography, 3D renders, generic device mockups, or ornamental stock art.
- No detached infographic cards, decorative data, unsupported claims, or hidden provenance.
- No on-screen paragraph that duplicates the voiceover.
- No implication that MindrianOS validates opportunities or chooses what the person should pursue.
