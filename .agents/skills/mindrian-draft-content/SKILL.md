---
name: mindrian-draft-content
description: Required before drafting or revising Mindrian blog posts, social posts, newsletters, landing copy, press releases, case studies or technical guides. Prepare the reader brief and apply the installed canonical brand rules before prose.
---

# Mindrian content production

This is the Mindrian adaptation of Anthropic's draft-content capability, revised 20 October 2026. Its original source, pinned provenance and Apache-2.0 license remain in the package skills/draft-content/upstream/. The original is reference material, not an alternate execution policy.

## Before drafting

Run the installed mindrian-production preflight for the actual task. tools check must find the required skills; use tools install --apply for supported missing tools. For prose, the content preparation command also checks the static writing tool profile. For generated images, visual aids or animation, use their specific task and meaningful renderer before creation. Never downgrade required interaction because a component package is absent.


1. Use the user's existing brief and the project's Mindrian intake. Do not invent missing identity, what/how/why, reader JTBD or research. On first use, complete the mindrian-brand-book intake/configure/adopt procedure. Run `npx --no-install mos-brand doctor`; resolve changed sources or edited managed files before production.
2. Read the actual local `references/brand-context.md` beside this installed skill. It contains the selected voice, text hierarchy, callout, quote, evidence, typography and pipeline rules. If using the skill directly from the package, `content prepare` below returns those complete instructions. Do not proceed on links or remembered rules alone.
3. Complete a real piece brief from the package's selected content-brief.json template. It needs speaker, reader situation/JTBD/evidence status, channel, topic, takeaway, desired action, language, length, outline, sources, claim status, missing material and visual purpose. Ask only for missing information. An empty source list requires an explicit evidence gap; it does not allow unsupported facts.
4. Start `mos-brand run start --kind content`. Run `mos-brand content prepare --id <run-id> --brief brief.json`. A NEEDS-INPUT result is a pre-draft stop: ask its missing questions. On content-ready, read the returned brandInstructions and appliedPlan. They contain the actual rules and how this brief will use them, not only file routes.
5. Save the brief and scan outline as the run's brief-stage output. Obtain the existing brief-stage review before drafting. The CLI blocks advancement without a current preparation record and rejects changes to the bound brief. Review records are attestations, not authenticated identities. An approved plan or permission to draft never authorizes unrelated spending, publishing or messaging.

## Produce and check

For articles, follow the installed blog pipeline: open the local task, plan, optionally measure, check overlap/refresh, write, validate claims, make visuals, review, register/ship when authorized, then verify the live page. Use the verified project profile to locate tools, paths and checks. Other channels use the channel guidance, without adding blog metadata or a website deployment task.

Apply the canonical voice before prose: recognizable situation, useful distinction, concrete example, question or practical next move. MindrianOS is the system and Theo the thinking partner. Show changing conditions and uncertainty honestly when relevant. The quest is not a compulsory illustration or structure for every article.

Build a meaningful scan path. Do not make a wall of text. A heading, bold phrase, callout or social excerpt must preserve the qualification in the body. Keep direct quotations exact and attributable. Separate facts, inferences, hypotheses, illustrations and current versus planned capabilities. Missing proof, quotes, customer results and numbers belong in a missing-material list, not invented publication copy. Never use em dashes.

Inspect original evidence; test instructions in their stated environment. Theo can guide the method but is not proof about a case. Optional paid research needs its actual estimate and explicit authorization. Load the actual tools/skills you use; unavailable tools remain pending, not passed. Preserve the project's working architecture and apply current brand rulings over retired visual rules.

Use `mos-brand review --file draft.md` and optionally `--evidence evidence.json` for structural and declared-record checks. Review actual rendered desktop/mobile reading and reduced-motion behavior when applicable. For blog art, `mos-brand image brief --article draft.md` keeps the article in charge of the composition and the brand in charge of style.

Handoff includes the draft, sources, visual provenance, actual verdicts/checks, missing material and unresolved reviews. Do not publish or send without authorization. No CLI or skill can prove the author read instructions, verify all facts or replace actual editorial judgment.
