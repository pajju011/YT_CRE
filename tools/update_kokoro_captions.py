import argparse
import json
from pathlib import Path
import re
import sys
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent

parser = argparse.ArgumentParser(description="Update captions from Kokoro audio")
parser.add_argument("--project", default="shorts/short-2-math", help="Project relative path")
args = parser.parse_args()

PROJECT_DIR = ROOT / args.project
BEATS = PROJECT_DIR / "beats.json"
AUDIO = PROJECT_DIR / "output/kokoro"

# Infer shot directory under remotion/src/shots
# e.g. short-2-math -> short-2, short-1-chess -> short-1
match = re.search(r"short-(\d+)", args.project)
if match:
    shot_dir_name = f"short-{match.group(1)}"
else:
    shot_dir_name = Path(args.project).name

OUTPUT = ROOT / f"remotion/src/shots/{shot_dir_name}/vo.gen.ts"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

if not BEATS.exists():
    print(f"Error: {BEATS} not found!")
    sys.exit(1)

with open(BEATS, encoding="utf-8") as f:
    data = json.load(f)

lines = []
for i, line in enumerate(data.get("vo", []), 1):
    wav = AUDIO / f"line_{i:02d}.wav"
    if not wav.exists():
        # Fallback to estimated timing if wav is missing
        duration = float(line.get("end", line.get("start", 0) + 2.0)) - float(line.get("start", 0))
    else:
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

print(f"✓ Kokoro caption timings generated for {shot_dir_name}!")
print("Updated:", OUTPUT)
