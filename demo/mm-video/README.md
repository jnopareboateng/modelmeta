# modelmeta demo film

This directory contains the Remotion source for the modelmeta demo film: a 44.95-second square composition showing portable model checkpoint metadata, SHA-256 linkage, inspection, and offline verification.

## Render

```bash
npm install
npm run lint
npx remotion render ModelmetaDemo ../modelmeta-demo.mp4 --concurrency=2
```

Create the lightweight GIF preview from the rendered MP4:

```bash
ffmpeg -i ../modelmeta-demo.mp4 -vf "fps=12,scale=480:-1:flags=lanczos" -loop 0 ../modelmeta-demo.gif
```

Preview the composition in Remotion Studio:

```bash
npx remotion studio --no-open
```

## Composition

- `src/Demo.tsx` — five-scene composition, transitions, layout, captions, and sound cues.
- `src/Composition.tsx` — `ModelmetaDemo` registration at 1080×1080, 30fps.
- `src/data.ts` — deterministic scatter data used by the chart scene.
- `public/vo/` — the aligned Deepgram Flux Hannah narration clips.
- `public/sfx/` — deterministic procedural UI sound effects.

The composition uses `@remotion/transitions`. Scene audio starts after the transition entrance window so narration and visual handoffs do not overlap.

The generated deliverables live one directory above this project: [`../modelmeta-demo.mp4`](../modelmeta-demo.mp4) and [`../modelmeta-demo.gif`](../modelmeta-demo.gif). The user-facing overview is [`../README.md`](../README.md).
