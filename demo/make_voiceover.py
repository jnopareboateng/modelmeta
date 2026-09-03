"""Regenerate the film's narration as ONE voice, guaranteed uniform.

Run from the repo root:  python demo/make_voiceover.py
Requires: OPENROUTER_API_KEY + MODEL_ID in the repo-root .env (never committed),
          ffmpeg + ffprobe on PATH, faster-whisper (uv pip install faster-whisper).

Method: a single TTS request renders the whole script in one generation, so
timbre, pace and character cannot drift between scenes (separate requests can
never guarantee that, even at low temperature). Scenes are joined with
[long-break] markers, then split at word-exact boundaries found by local
forced alignment (faster-whisper word timestamps on each scene's last word).
Silence-length heuristics were tried and failed: [long-break] pauses are no
longer than ordinary sentence pauses, so length-ranking picks wrong cuts.

Direction uses fish-audio S2 [bracket] cues (one primary direction per
sentence, slow keynote delivery), temperature=0.2, normalize on.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import urllib.request

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
ENV_PATH = REPO_ROOT / ".env"
OUT_DIR = REPO_ROOT / "demo" / "mm-video" / "public" / "vo"

LINES = {
    "s1": "[calm, warm narrator, speaking slowly and clearly] Every training run ends the same way. [soft tone] A file full of weights, with no memory of how it got there.",
    "s2": "[warm and steady, speaking slowly] Three hundred students. Study hours in, exam scores out. [confident] A real model, trained in under half a second.",
    "s3": "[calm, speaking slowly and clearly] modelmeta stamps it. One call binds the metadata to the bytes. [confident] Hash linked. Timed automatically.",
    "s4": "[relaxed, warm narrator] Inspect it anywhere. The dataset. The accuracy. The training time. [soft tone] No server. No account.",
    "s5": "[calm] Verify before you load. [confident] Match means safe. [firm] And when a single byte changes, it gets caught.",
    "s6": "[warm, speaking slowly] Models forget. [soft tone] Sidecars don't. [confident] modelmeta.",
}

# Last spoken word of scenes 1-5; each is unique in the script.
ANCHORS = ["there", "second", "automatically", "account", "caught"]


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


def synthesize(api_key: str, model: str, text: str) -> bytes:
    payload = {
        "model": model,
        "input": text,
        "response_format": "mp3",
        "temperature": 0.2,
        "normalize": True,
    }
    request = urllib.request.Request(
        "https://openrouter.ai/api/v1/audio/speech",
        data=json.dumps(payload).encode(),
        headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        return response.read()


def duration(path: pathlib.Path) -> float:
    proc = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=30,
    )
    return float(proc.stdout.strip())


def main() -> None:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise SystemExit("faster-whisper required: uv pip install faster-whisper")
    env = load_env(ENV_PATH)
    api_key = env.get("OPENROUTER_API_KEY", "")
    model = env.get("MODEL_ID", "")
    if not api_key or not model:
        raise SystemExit("OPENROUTER_API_KEY and MODEL_ID must be set in .env")

    keys = list(LINES.keys())
    script = " [long-break] ".join(LINES.values())
    print(f"single-take script: {len(script)} chars")
    audio = synthesize(api_key, model, script)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp.write(audio)
        full = pathlib.Path(tmp.name)
    try:
        whisper = WhisperModel("base.en", device="cpu", compute_type="int8")
        segments, _ = whisper.transcribe(str(full), word_timestamps=True, vad_filter=True)
        words = [
            (w.word.strip(" .,!?").lower(), w.start, w.end)
            for segment in segments
            for w in segment.words
        ]
        ends: list[float] = []
        for anchor in ANCHORS:
            matches = [(s, e) for (w, s, e) in words if w == anchor]
            if not matches:
                raise SystemExit(f"anchor word missing from alignment: {anchor}")
            ends.append(matches[0][1] + 0.3)
        total = duration(full)
        bounds = [0.0, *ends, total]
        for i, name in enumerate(keys):
            start = max(0.0, bounds[i] - (0.05 if i > 0 else 0.0))
            out = OUT_DIR / f"{name}.mp3"
            subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                 "-ss", f"{start:.3f}", "-to", f"{bounds[i + 1]:.3f}",
                 "-i", str(full), "-c:a", "libmp3lame", "-b:a", "128k", str(out)],
                check=True, timeout=120,
            )
            print(f"{name}: {duration(out):.2f}s")
    finally:
        full.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
