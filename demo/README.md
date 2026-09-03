# modelmeta demo

**Models forget. Sidecars don't.** A 46-second narrated film + a reproducible example.

![demo](modelmeta-demo.gif)

`modelmeta-demo.mp4` (1080×1080, AAC narration) is the full-quality cut.

## The example

`examples/` holds a real trained model and its sidecar — no mocks:

- `score_model.pkl` — regression (study hours → exam score), 300 students, R² 0.9213
- `score_model.pkl.modelmeta.yaml` — hash-linked sidecar: dataset digest, accuracy,
  auto-filled `wall_hours`, checkpoint SHA-256

Verify it with [modelmeta](https://github.com/jnopareboateng/modelmeta):

```bash
modelmeta inspect examples/score_model.pkl
modelmeta verify examples/score_model.pkl   # exit 0: match
```

## Reproduce the example

From the repo root:

```bash
uv pip install scikit-learn
python demo/make_example.py   # rewrites demo/examples/*, verifies clean
```

The plotted points behind the film's scatter scene live in `mm-video/src/data.ts`.

## Re-render the film

```bash
cd demo/mm-video
npm i
npx remotion render ModelmetaDemo ../modelmeta-demo.mp4
```

The film is 100% deterministic code (`mm-video/src/Demo.tsx`) — real run numbers,
no stock footage.

## The film

Directed narration, real run numbers, deterministic code. Source under `mm-video/`.
