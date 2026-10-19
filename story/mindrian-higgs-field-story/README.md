# MindrianOS — A Field of Opportunity

This is a new visual version of the roughly 59-second MindrianOS explainer. It uses the Higgs field only as a visual analogy for shared context: a research room can connect material, questions, evidence, and decisions so multiple opportunity candidates can be revisited and developed.

The previous cut remains in `../mindrian-opportunity-story/`. This version reuses the approved English narration and rebuilds the visual story with the Mindrian website's Theo-face system.

## Review locally

- Local review page: `review.html`
- Storyboard: `boards/storyboard.html`
- Rendered video: `renders/mindrian-higgs-field-v2.mp4`
- Editable HyperFrames composition: `index.html`
- Narration: `SCRIPT.md` and `assets/audio/narration.mp3`
- Eight editable scene compositions: `compositions/higgs-field/`

Start the persistent Studio preview from this directory:

```bash
npx hyperframes preview --background
```

Check it with:

```bash
npx hyperframes preview --status
```

Validate with `npm run check`. This version passed with zero lint/runtime warnings, zero layout/motion findings, and all 103 contrast checks passing.
