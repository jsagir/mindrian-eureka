# MindrianOS opportunity story

An approximately 59-second, 16:9 HyperFrames explainer draft. It follows one arc: scattered research → a user-framed question → methods chosen for the job → evidence-linked candidates → a growing opportunity portfolio.

This is a **product vision** story. On-screen records are illustrative. The narration does not claim that every step is shipped or that the current RS run validated an opportunity.

## Review locally

- Storyboard and narration player: `boards/storyboard.html`
- Editable HyperFrames composition: `index.html`
- Narration script: `SCRIPT.md`
- ElevenLabs MCP voice file: `assets/audio/narration.mp3`
- Scene plan: `STORYBOARD.md`
- Visual system: `design.md`

Open the HyperFrames Studio preview from the project root:

```bash
npx hyperframes preview --background
```

The preview is editable and reloads when files change. Stop it with:

```bash
npx hyperframes preview --stop
```

Validate after edits:

```bash
npm run check
```

Render only after the final preview is approved:

```bash
npm run render
```

The ElevenLabs API credential is read from Claude Code's local MCP configuration at generation time; it is not stored in this project.
