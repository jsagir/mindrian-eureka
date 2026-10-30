---
name: mindrian-production
description: Required preflight before creating Mindrian blogs, images, visual aids or animation. Inspect the actual project tools, install supported missing skills and dependencies, and apply selected brand instructions before production.
---

# Prepare the production environment

Read the actual selected rules in this skill's `references/brand-context.md` before making the deliverable. Run `npx --no-install mos-brand doctor`, then `mos-brand tools check --task <blog|image|visual-aid|animation> --renderer <method>`. Choose the method from the explanatory job, not from which package happens to be installed.

If supported skills or dependencies are missing, preview `mos-brand tools install` with the same task and renderer, then apply with `--apply` within the user's installation authorization. It protects managed edits and preserves existing dependencies. It installs only the registry's bundled skills and exact npm dependencies; do not substitute arbitrary install commands from a draft or third-party file. A different package manager, incompatible versions, unknown skill source or provider/account setup needs explicit resolution. Do not label it passed.

Before asset creation, complete a production brief with explain, change, interaction (none/local/scroll) and renderReason. Run `mos-brand tools prepare --task <task> --renderer <method> --brief production.json`. Read the actual returned brandInstructions and explanationPlan before creation. A missing tool or incomplete explanation stops preparation. For blogs, also complete the content run and content prepare procedure before prose; tools prepare does not replace the reader brief.

Use static HTML/SVG for a genuine still explanation. Use css for a finite local animation, react for stateful interaction, react-scroll for the defined continuous story/flipbook, image for provider-generated raster art, and video for a rendered-video host. Static build output does not imply React is forbidden elsewhere. A missing packaged component library does not justify removing required movement or inventing an import API. Reuse the actual examples, retain existing build architecture and review the rendered result.

For external generation, discover the actual live host capability first. .mindrian/tools.json can record a capability name, available=true and evidence of the live check under capabilities, but this is an operator declaration, not CLI-authenticated account access. Never include credentials. Recheck in the active host before invoking it. Paid usage and publishing need their existing authorization. The CLI installs tools; it does not claim to create, visually approve or fact-check the output.
