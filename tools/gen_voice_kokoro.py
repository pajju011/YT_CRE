import argparse
import json
from pathlib import Path
import sys

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

ROOT = Path(__file__).resolve().parent.parent

parser = argparse.ArgumentParser(description="Kokoro ONNX Voice Generator")
parser.add_argument("--project", default="shorts/short-2-math", help="Project relative path")
parser.add_argument("--voice", default="af_heart", help="Kokoro voice name")
parser.add_argument("--speed", type=float, default=1.0, help="Speech speed multiplier")
args = parser.parse_args()

PROJECT_DIR = ROOT / args.project
BEATS = PROJECT_DIR / "beats.json"
if not BEATS.exists():
    print(f"Error: {BEATS} not found!")
    sys.exit(1)

MODEL = ROOT / "models/kokoro/kokoro-v1.0.int8.onnx"
VOICES = ROOT / "models/kokoro/voices-v1.0.bin"

OUTPUT_DIR = PROJECT_DIR / "output/kokoro"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

VOICE = args.voice
SPEED = args.speed

print(f"Loading Kokoro model for project: {args.project}...")
model = Kokoro(str(MODEL), str(VOICES))

with open(BEATS, encoding="utf-8") as f:
    data = json.load(f)

lines = data.get("vo", [])
sample_rate = 24000
duration_sec = data.get("format", {}).get("durationSec", 42)
final_audio = np.zeros(int(duration_sec * sample_rate), dtype=np.float32)

print(f"Generating {len(lines)} narration lines with voice '{VOICE}'...")

for i, line in enumerate(lines):
    text = line["text"]
    start = float(line["start"])

    print(f"{i + 1}/{len(lines)}: {text}")

    samples, rate = model.create(
        text,
        voice=VOICE,
        speed=SPEED,
        lang="en-us"
    )

    samples = np.asarray(samples, dtype=np.float32)
    clip_path = OUTPUT_DIR / f"line_{i + 1:02d}.wav"
    sf.write(clip_path, samples, rate)

    start_sample = int(start * sample_rate)
    end_sample = min(
        start_sample + len(samples),
        len(final_audio)
    )

    if start_sample < len(final_audio):
        final_audio[start_sample:end_sample] += samples[:end_sample - start_sample]

    duration = len(samples) / rate
    print(f"   Start: {start:.2f}s | Duration: {duration:.2f}s")

output = OUTPUT_DIR / "voice.wav"
sf.write(output, final_audio, sample_rate)

print("\n✓ Kokoro narration generated successfully!")
print("Output:", output)
