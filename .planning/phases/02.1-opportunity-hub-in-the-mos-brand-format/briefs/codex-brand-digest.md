# Codex brand digest

## ANSWER

Most layout, typography, token, and accessibility choices match the current book at mos-brand commit `9f4ee34`.
The material conflicts are graph-link semantics and motion, CDN versus offline loading, and a missing motion-setting ruling.
Keep all unresolved choices marked proposed; the UI-SPEC itself says it has not been rendered.

## EVIDENCE

- `02.1-UI-SPEC.md:13,17-22`: visual verification pending; book is authority; values must be sourced, no network, every claim says `candidate, not verified`.
- `experience/graph-visualization/entries/2026-10-21/GUIDE.md:7-9`: graph answers neighborhood/bridge questions; rankings use lists; fewer than about 15 nodes use a static diagram; title asks the graph question. UI-SPEC `:208-15,237-39` mostly aligns, but fixes “about 15” to 15 as a proposal.
- `.../GUIDE.md:17-27`: primary objects cobalt, members muted, bridges yellow with ink labels; filed links ink, engine links faint cobalt, bridge links thick yellow with red particles; words must identify link type; yellow is not text on paper.
- UI-SPEC `:276-84,303`: all proposed pairs are cobalt, crossing pairs stay cobalt, and engine types share one color. This conflicts with the guide's bridge-link treatment. UI-SPEC `:234-35,551` also removes all particles, conflicting with the guide's animated bridge link. Resolve or record an explicit owner ruling.
- `.../GUIDE.md:25,72-78`: link type cannot rely on color; graph labels/tips and list routes must expose meaning; rotation is optional, off by default, reduced-motion disabled. UI-SPEC `:225,230,283` supplies list/focus alternatives and words, but its no-hover-only behavior must remain true.
- `.../GUIDE.md:49-66`: reading panels keep source distinct from interpretation, use short plain copy, preserve hedges, and link to source records. UI-SPEC `:323-56` must keep those distinctions for both record and pair panels.
- `experience/layout/entries/2026-10-19/content.html:1`: 4 px spacing scale, 12-column desktop, six-column tablet, four-column phone, 20 px phone gutter, 1200 px inner maximum, 1600 px scene maximum; square/open frames and cards only for bounded objects. UI-SPEC `:55-75,158-80` mostly matches. Its 768/1024 breakpoints and 32 px tablet margin are proposals, not book values.
- `foundations/typography/entries/2026-10-19/content.html:1`: Figtree display, DM Sans body/UI, Heebo Hebrew proposal, JetBrains Mono identifiers; body 18 px, UI 16 px, caption 13-14 px; Latin measure 58-72 characters; no synthetic italics. UI-SPEC `:83-97` matches roles, but its 13 px floor at every size is stricter than the accessibility floor, which fails only below 13 px at 1024 px and wider.
- `foundations/tokens/entries/2026-10-19/asset-b1c43da20b.css:1`: exact paper/ink/white/soft/blue/red/yellow/quiet values; zero radius; 44 px button minimum; 3 px focus and offset; Hebrew font variables; reduced-motion animation reset. UI-SPEC `:34-48,69-75,103-24` must copy token bytes and keep relative font paths and license texts.
- `foundations/color/entries/2026-10-19/content.html:1`: blue means inquiry, red challenge/interruption, yellow possibility; line status needs words and patterns; color never alone conveys evidence. UI-SPEC `:112-24,270-99` mostly follows this; its red-on-quiet prohibition is correct.
- `experience/accessibility/entries/2026-10-19/content.html:1`: 44 px is a comfort target, 24 CSS px is the conditional WCAG target-size minimum; keep static content and correct DOM focus order; test keyboard, RTL, 320 px, 200% zoom, increased text spacing and screen reader.
- Same accessibility source: evidence opens through a named keyboard control, never hover alone, and returns focus. UI-SPEC `:180,225,230` aligns through lists, but needs the full named-control and focus-return check.
- Same accessibility source: substantial motion needs a visible motion setting; reduced-motion mode must not show dead pause/still controls. UI-SPEC `:551-59` removes motion in reduced mode but has no explicit normal-mode motion setting. Resolve whether camera/tour motion qualifies.
- `experience/visual-language/shaper/motion/entries/2026-10-20/GUIDE.md:15-35`: Shaper animations need one shared player, relevance, complete still, no ambient loops, reduced-motion fallback. UI-SPEC's settled graph and no-ambient-motion rule `:229,234-35,551-59` aligns; Shaper-specific React contracts do not apply unless Shaper is introduced.
- `experience/css-capabilities/entries/2026-10-23/GUIDE.md:18-25`: semantic base first; every CSS enhancement needs feature detection, explicit off switch, same facts/actions, tested fallback, reduced-motion gating, and a recorded behavior test. UI-SPEC `:559` aligns and defaults to no enhancement.
- Graph guide `.../GUIDE.md:90-93` asks for an exact, two-week-old npm pin and describes jsDelivr loading. UI-SPEC `:34,48-49,578-87` instead vendors locally to satisfy its no-network contract. Keep local loading, but record this as a project constraint overriding the example and preserve all license/third-party notices.
- `identity/theo/states/entries/2026-10-19/content.html:1`; UI-SPEC `:495-518`: use only the authored face-state meanings and source SVGs. Do not infer extra expressions or redraw the parent lockup.

## UNVERIFIED

- No UI rendering, screenshots, or `mos-brand context/review` run was performed.
- The references are current at mos-brand commit `9f4ee34`; the UI-SPEC records CLI `2.43.0` but still requires its intake and review.

## RISK

The UI-SPEC presents some choices as book-derived while they conflict with graph-guide link semantics and motion. Its visual checker sign-off is not visual evidence.

## NEXT

Have the planner reconcile the graph-link and motion conflicts, then record the remaining proposals before implementation.
