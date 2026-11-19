
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

ROOT = Path(__file__).resolve().parent.parent

MODEL = ROOT / "models/kokoro/kokoro-v1.0.int8.onnx"
VOICES = ROOT / "models/kokoro/voices-v1.0.bin"
BEATS = ROOT / "shorts/short-2-math/beats.json"

OUTPUT_DIR = ROOT / "shorts/short-2-math/output/kokoro"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

VOICE = "af_heart"
SPEED = 1.0

print("Loading Kokoro model...")

model = Kokoro(str(MODEL), str(VOICES))

with open(BEATS, encoding="utf-8") as f:
    data = json.load(f)

lines = data["vo"]

sample_rate = 24000
total_duration = 42
final_audio = np.zeros(total_duration * sample_rate, dtype=np.float32)

print(f"Generating {len(lines)} narration lines...")

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

print("\nKokoro narration generated!")
print("Output:", output)
print("Duration:", total_duration, "seconds")
