import json
from pathlib import Path
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
BEATS = ROOT / "shorts/short-2-math/beats.json"
AUDIO = ROOT / "shorts/short-2-math/output/kokoro"
OUTPUT = ROOT / "remotion/src/shots/short-2/vo.gen.ts"

with open(BEATS, encoding="utf-8") as f:
    data = json.load(f)

lines = []

for i, line in enumerate(data["vo"], 1):
    wav = AUDIO / f"line_{i:02d}.wav"

    if not wav.exists():
        raise FileNotFoundError(wav)

    duration = sf.info(wav).duration
    start = float(line["start"])
    end = start + duration

    lines.append({
        "text": line["text"],
        "start": round(start, 3),
        "end": round(end, 3)
    })

content = """// AUTO-GENERATED from Kokoro audio clip durations.
// Word positions are estimated by timeWords() in shorts.tsx.
import type { VoLine } from '../../lib/shorts';

export const VO: VoLine[] = [
"""

for line in lines:
    content += (
        "  { text: " + json.dumps(line["text"], ensure_ascii=False)
        + f", start: {line['start']}, end: {line['end']} }},\n"
    )

content += "];\n"

OUTPUT.write_text(content, encoding="utf-8")

print("Kokoro caption timings generated!")
for i, line in enumerate(lines, 1):
    print(f"{i:02d}. {line['start']:.2f}s - {line['end']:.2f}s")
print("Updated:", OUTPUT)
