# Codex contrast recompute

## ANSWER

The UI-SPEC's red-on-quiet ratio recomputes to 4.17:1, below 4.5:1 for ordinary text.
All four removed neighborhood tints are below 3:1 against paper; the drop decision is correct.
The template's 0.45-alpha blue line is about 1.79:1 against paper, below 3:1 for meaningful graphics.

## EVIDENCE

- Method: WCAG relative luminance. Convert each sRGB channel to linear light, use `0.2126R + 0.7152G + 0.0722B`, then `(Llighter + 0.05) / (Ldarker + 0.05)`. Alpha colors are composited over paper before the ratio.
- `foundations/tokens/entries/2026-10-19/asset-b1c43da20b.css:1`: quiet `#ECEAE2`, paper `#F7F5EE`, red `#D6281F`.
- Recompute `#D6281F` on `#ECEAE2`: `4.1683`, rounds to `4.17:1`. Ordinary text needs `4.5:1` per `experience/accessibility/entries/2026-10-19/content.html:1`.
- `network.template.html:158`: HOOD order contains `#c8a52a`, `#9a9a3c`, `#7aa35c`, `#c48a3a` at zero-based indices 2, 7, 10, 13.
- Recomputed on paper: `#c8a52a` = `2.17:1`; `#9a9a3c` = `2.73:1`; `#7aa35c` = `2.67:1`; `#c48a3a` = `2.73:1`. All fail the 3:1 non-text graphic target in `experience/accessibility/entries/2026-10-19/content.html:1`.
- `network.template.html:186`: engine-line color is `rgba(80,110,220,0.45)`. Composited at alpha 0.45 over paper, RGB rounds to `#ACB8E6`; contrast is `1.79:1`, below 3:1.
- `network.template.html:188` also sets `.linkOpacity(0.6)`. If the renderer multiplies this with the color alpha, effective alpha is 0.27 and contrast is `1.39:1`; renderer compositing was not independently inspected.
- UI-SPEC `:141,150` records the first two failing groups. UI-SPEC `:227` correctly replaces the template line with full-opacity brand cobalt; the book color report gives cobalt on paper as `7.63:1` at `foundations/color/entries/2026-10-19/content.html:1`.

## UNVERIFIED

The visual effect of simultaneous WebGL color alpha and `linkOpacity(0.6)` was not measured in the library renderer. Both calculated cases fail 3:1.

## RISK

Using the template line alpha, or either of the two opacities together, can make graph links too faint to meet the graphic contrast target.

## NEXT

Keep full-opacity cobalt for proposed links and retain the four tint exclusions in the implementation plan.
