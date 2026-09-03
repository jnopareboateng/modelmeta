# UPDATE_LOG — modelmeta

## 2026-09-03
- v3 Apple-grade cut is the deliverable (overwrote mp4/gif): Inter + JetBrains Mono via @fontsource (bundled, offline-safe), frosted glass + hairlines + grain + vignette, custom SVG link logo mark, zero emojis, fade-through-black scene transitions, real animated scatter (60 pts, staggered pop) + glowing trend line + traveler dot. All display numbers are the real run (R² 0.9213, 300 rows, 0.44s).
- v4 narrated cut (~46s, 1379f): fish-audio TTS via OpenRouter /audio/speech (onyx rejected with 400, used provider-default voice; key in modelmeta/.env, never printed/committed, .gitignore fixed after shell mangled newlines). @remotion/transitions cross-dissolves (24f), scenes retimed to VO+padding, Audio per scene via public/vo/. New repo jnopareboateng/modelmeta-demo pushed (film + VO + examples/score_model.pkl + sidecar, verifies match/0). modelmeta main pushed clean (6298838).
- v4.1 motion fix (pushed 4061fe2): cross-dissolve bled incoming typing over outgoing scenes (TransitionSeries plays incoming from local frame 0 during overlap) → per-scene black entrance veil + IN=0.8s shift baked into all timing helpers; trend line/halo/glow escaped plot panel → SVG clipPath on axes, clamped endpoints, halo 18→13. Verified at dissolve/plot/corrupt frames, re-rendered + gif.
- v4.2 voice direction (pushed 3094a8c): model is fish-audio/s2.1-pro-free:free; no audio tags were used before (the robotic flatness). Now S2 [bracket] direction per fish docs (calm/warm/confident/soft, slow delivery) + temperature 0.2 + normalize. OpenRouter supported_voices is null for this model → no voice IDs exist; single fixed character via provider-default voice + low temp. Scene 4 extended 255→313f for the 8.93s narration; total 1437f (~48s).
- Universal regression E2E (synthetic study-hours→exam-score, 300 rows, HGBR): R² 0.9213, RMSE 4.14, 0.44s; stamp→verify match/0→corrupt→digest_mismatch/12. `E2E OK`.
- 30s demo video built with official Remotion skill files read directly from Codex plugin cache (remotion@openai-curated shows not-installed in CLI but files present; no instavar plugin found anywhere). Project: `~/projects/justjosh/modelmeta-demo/mm-video` (ModelmetaDemo, 1080x1080, 900f). Outputs: `modelmeta-demo.mp4` (2.3MB) + `modelmeta-demo.gif` (1MB, 480px). Frames spot-checked.
- Note: /tmp wiped between sessions (e2e_pkgs + mm_demo lost, rebuilt via uv --target). Scratch test scripts live in Windows Temp/opencode, not committed.

## 2026-09-02
- Implemented auto-timing in `MetaWriter` (monotonic `wall_hours`/`gpu_hours` auto-fill, `reset_timer()`, `elapsed_*` props) + `schema` wall_hours validation + `inspect` duration display; rewrote README top to beginner one-line problem + 30-sec flow. 136 tests pass.
- Review flaw noted: no GPU detection (count is caller-supplied only), `stamp_checkpoint` fresh writer gives ~0; durable resume ledger still TODO. Process correction: agents must use deep reasoning (j-space) and adversarial flaw scan before coding.

## 2026-08-21
- Researched competitive landscape, PMF, and technical feasibility (3 parallel agents). Verdict: build as narrow integrity tool; wedge = `verify` pre-load gate on pickle-CVE timeline. Docs: `docs/research/2026-08-21-pmf-and-landscape.md`.
- Amended spec (§19): Python >=3.11, rfc8785 library pinned, YAML anchors/aliases rejected + 4 MiB cap, Windows replace retry, inode degradation, unsupported_schema -> exit 13.
- Designed system architecture (`docs/architecture.md`): dict-native data model, strict loader, atomic write sequence, stable exit codes, test matrix mapped to acceptance criteria.
- Implemented v0.1.0 via feature branches (`feat/tooling-foundation`, `feat/hashing-writer`, `feat/read-verify-cli`) merged through `dev` into `main`.
- Gates at release: 137 tests pass (incl. 16 GiB sparse >memory acceptance test, ~4 min), ruff clean, mypy strict clean, wheel builds and installs; e2e verified stamp -> verify(0) -> corrupt -> verify(12).
- Note: `.githooks/pre-push` runs the full suite (~5 min incl. slow test). Use `--no-verify` for iteration pushes after running gates manually.
