"""Regenerate the film's narration as ONE voice, guaranteed uniform.

Run from the repo root:  python demo/make_voiceover.py
Requires: DEEPGRAM_API_KEY in the repo-root .env (never committed),
          ffmpeg + ffprobe on PATH, faster-whisper (uv pip install faster-whisper).

Method: a single TTS request (Deepgram Flux, fixed voice model) renders the
whole pitch in one generation, so timbre, pace and character cannot drift
between scenes. Scenes are then split at word-exact boundaries found by local
forced alignment (faster-whisper word timestamps on each scene's last word).

Voice: flux-hannah-en on POST /v2/speak, expressivity=1 (salesman energy).
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import tempfile
import urllib.request

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
ENV_PATH = REPO_ROOT / ".env"
OUT_DIR = REPO_ROOT / "demo" / "mm-video" / "public" / "vo"

VOICE_MODEL = "flux-hannah-en"

LINES = {
    "s1": (
        "A model is more than its weights. But the data, score, training time, "
        "and exact bytes rarely travel with them."
    ),
    "s2": (
        "A real run: three hundred students. Study hours in. Exam scores out. "
        "Training takes less than half a second. Fast."
    ),
    "s3": (
        "One call with modelmeta stamps the model and writes a sidecar: dataset, "
        "accuracy, runtime, and a SHA two five six link, next to the file - portable."
    ),
    "s4": "Inspect it anywhere. The whole story travels with the file. Offline.",
    "s5": (
        "Verify before loading. Match. Change one byte? The gate stops. Models "
        "forget. Sidecars don't. Install modelmeta today."
    ),
}

# Final word of scenes 1-5; backward search takes the last occurrence, so a
# repeated word is fine as long as its LAST use ends the scene. Must be the
# TRUE final word (mid-scene anchors shift every later cut), aligner-stable
# (no digits/percent: those render as numerals), apostrophe-stripped.
ANCHORS = ["bytes", "fast", "portable", "offline", "today"]


def load_env(path: pathlib.Path) -> dict[str, str]:
    vals: dict[str, str] = {}
    with open(path) as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            vals[key.strip()] = value.strip().strip("'").strip('"')
    return vals


def synthesize(api_key: str, text: str) -> bytes:
    url = f"https://api.deepgram.com/v2/speak?model={VOICE_MODEL}&expressivity=1&speed=1.15"
    request = urllib.request.Request(
        url,
        data=json.dumps({"text": text}).encode(),
        headers={"Authorization": "Token " + api_key, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        return response.read()


def duration(path: pathlib.Path) -> float:
    proc = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return float(proc.stdout.strip())


def main() -> None:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise SystemExit("faster-whisper required: uv pip install faster-whisper") from None
    env = load_env(ENV_PATH)
    api_key = env.get("DEEPGRAM_API_KEY", "")
    if not api_key:
        raise SystemExit("DEEPGRAM_API_KEY must be set in .env")

    keys = list(LINES.keys())
    script = "\n\n".join(LINES.values())
    print(f"single-take script: {len(script)} chars, voice {VOICE_MODEL}")
    audio = synthesize(api_key, script)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp.write(audio)
        full = pathlib.Path(tmp.name)
    try:
        whisper = WhisperModel("base.en", device="cpu", compute_type="int8")
        segments, _ = whisper.transcribe(str(full), word_timestamps=True, vad_filter=True)
        words = [
            (w.word.strip(" .,!? '" + '"' + "\u2019").lower(), w.start, w.end)
            for segment in segments
            for w in segment.words
        ]
        ends: list[float] = []
        for anchor in ANCHORS:
            matches = [(s, e) for (w, s, e) in words if w == anchor]
            if not matches:
                raise SystemExit(f"anchor word missing from alignment: {anchor}")
            if len(matches) > 1:
                print(f"note: anchor {anchor!r} occurs {len(matches)}x, using last")
            ends.append(matches[-1][1] + 0.3)
        for anchor in ANCHORS:
            hits = [(s, e) for (w, s, e) in words if w == anchor]
            print(f"anchor {anchor}: {hits[-1][0]:.2f}-{hits[-1][1]:.2f}")
        total = duration(full)
        bounds = [0.0, *ends, total]
        for i, name in enumerate(keys):
            start = max(0.0, bounds[i] - (0.05 if i > 0 else 0.0))
            out = OUT_DIR / f"{name}.mp3"
            subprocess.run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-ss",
                    f"{start:.3f}",
                    "-to",
                    f"{bounds[i + 1]:.3f}",
                    "-i",
                    str(full),
                    "-c:a",
                    "libmp3lame",
                    "-b:a",
                    "128k",
                    str(out),
                ],
                check=True,
                timeout=120,
            )
            print(f"{name}: {duration(out):.2f}s")
    finally:
        full.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
