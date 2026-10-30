# Relevant Mindrian design context

Consumer: MindrianOS Eureka Opportunity Hub

Read shared rules first, then the smallest task segments. Context/dependency segments preserve inheritance; they do not mean load every descendant.

- /m:os - Brand Manager (context): CONTEXT.md
  Reason: Ancestor of governance; inherits-from governance; Ancestor of foundations; inherits-from foundations; Ancestor of writing; inherits-from writing; Ancestor of experience; inherits-from experience; Ancestor of identity; inherits-from identity; Ancestor of family; inherits-from family; Ancestor of teams; inherits-from teams
- Experience (context): segments/experience/CONTEXT.md
  Reason: Ancestor of experience/layout; inherits-from experience/layout; Ancestor of experience/inner-pages; inherits-from experience/inner-pages; Ancestor of experience/narrative; inherits-from experience/narrative; Ancestor of experience/accessibility; inherits-from experience/accessibility; Ancestor of experience/css-capabilities; inherits-from experience/css-capabilities; Ancestor of experience/forms; inherits-from experience/forms; Ancestor of experience/graph-visualization; inherits-from experience/graph-visualization; Ancestor of experience/motion; inherits-from experience/motion; Ancestor of experience/faq; inherits-from experience/faq; Ancestor of experience/visual-language; inherits-from experience/visual-language
- Accessibility and quality (task): segments/experience/accessibility/CONTEXT.md
  Reason: Declared surface: website; Declared surface: app-ui; Declared surface: graph-visualization; uses experience/css-capabilities; uses identity/logo/favicons; uses experience/forms; uses experience/graph-visualization; uses writing/text-augmentation; uses experience/forms/engagement; uses teams/documentation
- CSS capabilities (task): segments/experience/css-capabilities/CONTEXT.md
  Reason: Declared surface: website; Declared surface: app-ui
- FAQs and help: answer the decision behind the question (dependency): segments/experience/faq/CONTEXT.md
  Reason: uses teams/marketing
- Forms and interface copy: every field needs a job (task): segments/experience/forms/CONTEXT.md
  Reason: Declared surface: app-ui; uses teams/marketing; Ancestor of experience/forms/engagement; inherits-from experience/forms/engagement; Ancestor of experience/forms/access; inherits-from experience/forms/access
- Website access: Google sign-in where the product needs an identity, optional introduction (task): segments/experience/forms/access/CONTEXT.md
  Reason: Active ruling set website-google-access
- Proposed: CTAs and forms as a marketing and learning gateway (dependency): segments/experience/forms/engagement/CONTEXT.md
  Reason: uses experience/forms; uses teams/marketing
- Proposed: graph visualization (task): segments/experience/graph-visualization/CONTEXT.md
  Reason: Declared surface: graph-visualization
- Building inner pages as places in the same story (task): segments/experience/inner-pages/CONTEXT.md
  Reason: Declared surface: website
- Layout and components (task): segments/experience/layout/CONTEXT.md
  Reason: Declared surface: website; Declared surface: app-ui; uses teams/documentation
- Motion grammar (task): segments/experience/motion/CONTEXT.md
  Reason: Declared surface: graph-visualization; uses experience/graph-visualization; uses experience/visual-language/shaper/motion
- How to build a visual story (task): segments/experience/narrative/CONTEXT.md
  Reason: Declared surface: website
- Visual explanation grammar (task): segments/experience/visual-language/CONTEXT.md
  Reason: Active ruling set visual-explanation-grammar; Ancestor of experience/visual-language/graph-data; inherits-from experience/visual-language/graph-data; Ancestor of experience/visual-language/graph-relationships; inherits-from experience/visual-language/graph-relationships; Ancestor of experience/visual-language/matrix-2x2; inherits-from experience/visual-language/matrix-2x2; Ancestor of experience/visual-language/pyramid; inherits-from experience/visual-language/pyramid; Ancestor of experience/visual-language/system; inherits-from experience/visual-language/system; Ancestor of experience/visual-language/framework; inherits-from experience/visual-language/framework; Ancestor of experience/visual-language/shaper; inherits-from experience/visual-language/shaper
- A framework as a way to look (dependency): segments/experience/visual-language/framework/CONTEXT.md
  Reason: uses experience/visual-language
- A graph of values (dependency): segments/experience/visual-language/graph-data/CONTEXT.md
  Reason: uses experience/visual-language
- A graph of relationships (dependency): segments/experience/visual-language/graph-relationships/CONTEXT.md
  Reason: uses experience/visual-language
- A 2×2 matrix (dependency): segments/experience/visual-language/matrix-2x2/CONTEXT.md
  Reason: uses experience/visual-language
- A pyramid or hierarchy (dependency): segments/experience/visual-language/pyramid/CONTEXT.md
  Reason: uses experience/visual-language
- Shaper React framework components (dependency): segments/experience/visual-language/shaper/CONTEXT.md
  Reason: uses experience/visual-language; Ancestor of experience/visual-language/shaper/motion; inherits-from experience/visual-language/shaper/motion
- Shaper motion ruling and relevance player (task): segments/experience/visual-language/shaper/motion/CONTEXT.md
  Reason: Active ruling set shaper-motion-ruling; uses experience/visual-language/shaper
- A system, flow or feedback loop (dependency): segments/experience/visual-language/system/CONTEXT.md
  Reason: uses experience/visual-language
- Family (dependency): segments/family/CONTEXT.md
  Reason: uses identity/logo/favicons
- Foundations (context): segments/foundations/CONTEXT.md
  Reason: Ancestor of foundations/positioning; inherits-from foundations/positioning; Ancestor of foundations/master-story; inherits-from foundations/master-story; Ancestor of foundations/typography; inherits-from foundations/typography; Ancestor of foundations/tokens; inherits-from foundations/tokens; Ancestor of foundations/color; inherits-from foundations/color; Ancestor of foundations/quest; inherits-from foundations/quest
- Color and meaning (task): segments/foundations/color/CONTEXT.md
  Reason: Declared surface: graph-visualization; uses experience/graph-visualization
- The story architecture (mandatory): segments/foundations/master-story/CONTEXT.md
  Reason: Shared baseline; uses writing/voice; uses teams/marketing
- The brand in plain words (mandatory): segments/foundations/positioning/CONTEXT.md
  Reason: Shared baseline; uses teams/marketing
- The quest, uncertainty and changing conditions (dependency): segments/foundations/quest/CONTEXT.md
  Reason: uses foundations/positioning; uses foundations/master-story; uses teams/marketing/draft-content; uses experience/forms/engagement
- tokens (task): segments/foundations/tokens/CONTEXT.md
  Reason: Declared surface: website; Declared surface: app-ui; Declared surface: graph-visualization
- Fonts and typography in English and Hebrew (task): segments/foundations/typography/CONTEXT.md
  Reason: Declared surface: website; Declared surface: graph-visualization; uses writing/text-augmentation; Ancestor of foundations/typography/figtree; inherits-from foundations/typography/figtree; Ancestor of foundations/typography/dm-sans; inherits-from foundations/typography/dm-sans; Ancestor of foundations/typography/heebo; inherits-from foundations/typography/heebo; Ancestor of foundations/typography/jetbrains-mono; inherits-from foundations/typography/jetbrains-mono
- dm sans (dependency): segments/foundations/typography/dm-sans/CONTEXT.md
  Reason: uses foundations/typography
- figtree (dependency): segments/foundations/typography/figtree/CONTEXT.md
  Reason: uses foundations/typography
- heebo (dependency): segments/foundations/typography/heebo/CONTEXT.md
  Reason: uses foundations/typography
- jetbrains mono (dependency): segments/foundations/typography/jetbrains-mono/CONTEXT.md
  Reason: uses foundations/typography
- Governance (context): segments/governance/CONTEXT.md
  Reason: Ancestor of governance/intake; inherits-from governance/intake; Ancestor of governance/tooling; inherits-from governance/tooling
- Consumer entry workflow (mandatory): segments/governance/intake/CONTEXT.md
  Reason: Mandatory first workflow; uses governance/tooling
- Installable brand tooling (context): segments/governance/tooling/CONTEXT.md
  Reason: Ancestor of governance/tooling/production; inherits-from governance/tooling/production
- Project tools and production preflight (task): segments/governance/tooling/production/CONTEXT.md
  Reason: Active ruling set production-tool-preflight
- Identity (context): segments/identity/CONTEXT.md
  Reason: Ancestor of identity/logo; inherits-from identity/logo; Ancestor of identity/theo; inherits-from identity/theo
- The logo system (task): segments/identity/logo/CONTEXT.md
  Reason: Declared surface: website; Ancestor of identity/logo/favicons; inherits-from identity/logo/favicons; Ancestor of identity/logo/variants; inherits-from identity/logo/variants
- Favicons and service icons (task): segments/identity/logo/favicons/CONTEXT.md
  Reason: Declared surface: website; Declared surface: app-ui
- variants (dependency): segments/identity/logo/variants/CONTEXT.md
  Reason: uses identity/logo
- Theo is one character (context): segments/identity/theo/CONTEXT.md
  Reason: Ancestor of identity/theo/states; inherits-from identity/theo/states; uses teams/documentation; Ancestor of identity/theo/framework-language; inherits-from identity/theo/framework-language
- The avatar as a framework and concept language (dependency): segments/identity/theo/framework-language/CONTEXT.md
  Reason: uses experience/visual-language; uses experience/visual-language/shaper
- The face state contract (task): segments/identity/theo/states/CONTEXT.md
  Reason: Declared surface: app-ui
- Teams (context): segments/teams/CONTEXT.md
  Reason: Ancestor of teams/marketing; inherits-from teams/marketing; Ancestor of teams/jtbd; inherits-from teams/jtbd; Ancestor of teams/documentation; inherits-from teams/documentation
- Documentation: help someone complete the job (dependency): segments/teams/documentation/CONTEXT.md
  Reason: uses experience/faq
- Mindrian uses its own method (dependency): segments/teams/jtbd/CONTEXT.md
  Reason: uses experience/forms; uses teams/marketing; uses experience/faq; uses teams/documentation
- Marketing: start with the job (context): segments/teams/marketing/CONTEXT.md
  Reason: Ancestor of teams/marketing/draft-content; inherits-from teams/marketing/draft-content
- Draft content for the reader job (task): segments/teams/marketing/draft-content/CONTEXT.md
  Reason: Declared surface: website; uses teams/documentation; Active ruling set content-production-pipeline
- Writing (context): segments/writing/CONTEXT.md
  Reason: Ancestor of writing/voice; inherits-from writing/voice; Ancestor of writing/punctuation; inherits-from writing/punctuation; Ancestor of writing/text-augmentation; inherits-from writing/text-augmentation; Ancestor of writing/editorial-integrity; inherits-from writing/editorial-integrity; Ancestor of writing/english-hebrew; inherits-from writing/english-hebrew
- Callouts, quotations and grounded claims (task): segments/writing/editorial-integrity/CONTEXT.md
  Reason: Declared surface: graph-visualization; uses teams/marketing/draft-content; uses experience/graph-visualization; uses writing/text-augmentation; Ancestor of writing/editorial-integrity/callouts; inherits-from writing/editorial-integrity/callouts; Ancestor of writing/editorial-integrity/quotations; inherits-from writing/editorial-integrity/quotations; Ancestor of writing/editorial-integrity/evidence; inherits-from writing/editorial-integrity/evidence; uses teams/documentation
- Callout roles and restrained emphasis (dependency): segments/writing/editorial-integrity/callouts/CONTEXT.md
  Reason: uses writing/editorial-integrity
- Claim-level research and technical verification (dependency): segments/writing/editorial-integrity/evidence/CONTEXT.md
  Reason: uses writing/editorial-integrity
- Exact quotation and visible attribution (dependency): segments/writing/editorial-integrity/quotations/CONTEXT.md
  Reason: uses writing/editorial-integrity
- English and Hebrew writing (dependency): segments/writing/english-hebrew/CONTEXT.md
  Reason: uses experience/forms
- punctuation (mandatory): segments/writing/punctuation/CONTEXT.md
  Reason: Shared baseline; uses writing/voice; uses experience/forms
- Text augmentation and scannable hierarchy (task): segments/writing/text-augmentation/CONTEXT.md
  Reason: Declared surface: graph-visualization; uses writing/voice; uses teams/marketing/draft-content; uses experience/forms/engagement
- The voice of Mindrian (mandatory): segments/writing/voice/CONTEXT.md
  Reason: Shared baseline; uses teams/marketing/draft-content; uses experience/graph-visualization; uses teams/marketing; uses experience/forms/engagement; uses experience/faq; uses teams/documentation

## Rule sets

- brand-baseline: active; checks-required-not-yet-executed (applicable scope)
- uiux-ruling-system: planned; not-implemented-not-passed (applicable scope)
- content-production-pipeline: active; checks-required-not-yet-executed (applicable scope)
- blog-production-pipeline: active; checks-required-not-yet-executed (outside declared scope)
- production-tool-preflight: active; checks-required-not-yet-executed (applicable scope)
- visual-explanation-grammar: active; checks-required-not-yet-executed (applicable scope)
- shaper-motion-ruling: active; checks-required-not-yet-executed (applicable scope)
- website-google-access: active; checks-required-not-yet-executed (applicable scope)
- graph-visualization-ruling: proposed; not-implemented-not-passed (applicable scope)
- css-capabilities-ruling: proposed; not-implemented-not-passed (applicable scope)
