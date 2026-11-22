#!/usr/bin/env python3
"""
auto_sound_designer.py — Automated Sound Design (SFX) Scorer & Audio Bus Mixer.

Analyzes narrative beats or storyboard scenes (Hook, Setup, Build, Reveal, Loop)
and intelligently places transition, tension, and climax sound effects from the
curated SFX library (media/library/sfx/clips/).

Outputs a multi-track mixed sfx_bus.wav synchronized to the exact video timeline.
"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
SFX_CATALOG_PATH = ROOT / "media" / "library" / "sfx" / "catalog.json"
SFX_CLIPS_DIR = ROOT / "media" / "library" / "sfx" / "clips"

# Curated high-impact sound design mappings
BEAT_SFX_RULES = [
    {
        "keywords": ["hook", "intro", "start", "scene_1", "scene 1"],
        "default_sfx": "whoosh-soft",
        "alt_sfx": "impact-soft",
        "gain_db": -8.0,
        "offset_s": 0.05,
        "desc": "Intro hook whoosh transition"
    },
    {
        "keywords": ["setup", "context", "scene_2", "scene 2"],
        "default_sfx": "page-flip",
        "alt_sfx": "ui-click-soft",
        "gain_db": -10.0,
        "offset_s": 0.0,
        "desc": "Story context scene transition"
    },
    {
        "keywords": ["build", "tension", "quiz", "question", "scene_3", "scene 3"],
        "default_sfx": "clock-tick-soft",
        "alt_sfx": "riser-soft",
        "gain_db": -12.0,
        "offset_s": 0.0,
        "desc": "Curiosity and tension buildup"
    },
    {
        "keywords": ["reveal", "climax", "secret", "answer", "scene_4", "scene 4"],
        "default_sfx": "pop-reveal",
        "alt_sfx": "chime-magic",
        "gain_db": -7.0,
        "offset_s": 0.05,
        "desc": "Rewarding reveal pop / climax hit"
    },
    {
        "keywords": ["twist", "scene_5", "scene 5"],
        "default_sfx": "sparkle-soft",
        "alt_sfx": "warm-shimmer",
        "gain_db": -10.0,
        "offset_s": 0.0,
        "desc": "Twist shimmer accent"
    },
    {
        "keywords": ["loop", "outro", "cta", "end", "scene_6", "scene 6"],
        "default_sfx": "whoosh-reverse",
        "alt_sfx": "warm-shimmer",
        "gain_db": -9.0,
        "offset_s": 0.0,
        "desc": "Seamless outro loop transition"
    }
]


def get_available_sfx():
    """Returns a dictionary of all available SFX clips."""
    sfx = {}
    if SFX_CATALOG_PATH.exists():
        try:
            with open(SFX_CATALOG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("clips", []):
                    sfx[item["id"]] = item
        except Exception as e:
            sys.stderr.write(f"[auto_sound_designer] Catalog read error: {e}\n")

    # Also scan disk directly
    if SFX_CLIPS_DIR.exists():
        for f in SFX_CLIPS_DIR.glob("*.mp3"):
            if f.stem not in sfx:
                sfx[f.stem] = {
                    "id": f.stem,
                    "file": f"clips/{f.name}",
                    "category": "sound-effect"
                }
    return sfx


def get_media_duration(file_path):
    """Probes exact duration in seconds using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(file_path)
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(res.stdout.strip())
    except Exception:
        return 30.0


def design_sfx_cues(beats_data, total_duration=None):
    """
    Intelligently scores a list of narrative beats or scene timestamps into SFX cues.
    
    Args:
        beats_data: List of beat dicts (e.g. [{'beat': 'hook', 'start': 0.0, 'end': 4.0}, ...])
        total_duration: Total video length in seconds (optional)
        
    Returns:
        List of cue dicts: [{'at_s': 0.1, 'sfx_id': 'whoosh-soft', 'gain_db': -8.0, 'cue': 'Hook whoosh'}, ...]
    """
    sfx_catalog = get_available_sfx()
    cues = []
    
    if not beats_data:
        # Default fallback cues for a generic ~15-30s short
        dur = total_duration or 20.0
        cues.append({"at_s": 0.05, "sfx_id": "whoosh-soft", "gain_db": -8.0, "cue": "Intro transition"})
        if dur > 6.0:
            cues.append({"at_s": 4.0, "sfx_id": "page-flip", "gain_db": -10.0, "cue": "Scene transition"})
        if dur > 12.0:
            cues.append({"at_s": 8.5, "sfx_id": "pop-reveal", "gain_db": -7.0, "cue": "Key reveal"})
        if dur > 16.0:
            cues.append({"at_s": max(1.0, dur - 2.5), "sfx_id": "whoosh-reverse", "gain_db": -9.0, "cue": "Outro loop"})
        return cues

    for idx, beat_item in enumerate(beats_data):
        b_name = str(beat_item.get("beat", f"scene_{idx+1}")).lower()
        b_title = str(beat_item.get("title", "")).lower()
        b_text = str(beat_item.get("text", "")).lower()
        start_time = float(beat_item.get("start", idx * 4.0))

        # Match against BEAT_SFX_RULES
        matched_rule = None
        for rule in BEAT_SFX_RULES:
            if any(k in b_name or k in b_title for k in rule["keywords"]):
                matched_rule = rule
                break

        if not matched_rule:
            # Fallback based on beat index
            if idx == 0:
                matched_rule = BEAT_SFX_RULES[0]  # Intro
            elif idx == len(beats_data) - 1:
                matched_rule = BEAT_SFX_RULES[5]  # Outro
            elif idx == len(beats_data) - 2:
                matched_rule = BEAT_SFX_RULES[3]  # Climax / Reveal
            else:
                matched_rule = BEAT_SFX_RULES[1]  # Transition

        sfx_id = matched_rule["default_sfx"]
        if sfx_id not in sfx_catalog and matched_rule["alt_sfx"] in sfx_catalog:
            sfx_id = matched_rule["alt_sfx"]

        # Ensure SFX exists
        if sfx_id in sfx_catalog:
            cue_time = max(0.0, round(start_time + matched_rule.get("offset_s", 0.0), 3))
            cues.append({
                "at_s": cue_time,
                "sfx_id": sfx_id,
                "gain_db": matched_rule.get("gain_db", -8.0),
                "cue": f"{matched_rule.get('desc', 'Transition')}: {b_name}"
            })

    # Sort cues chronologically
    cues.sort(key=lambda x: x["at_s"])
    return cues


def render_sfx_bus(cues, total_duration, out_wav_path):
    """
    Renders an audio bus WAV containing all positioned SFX events.
    """
    out_path = Path(out_wav_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    total_dur = max(1.0, float(total_duration or 30.0))

    if not cues:
        # Create silent audio track of requested duration
        cmd_silent = [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-t", f"{total_dur:.3f}",
            "-c:a", "pcm_s16le",
            str(out_path)
        ]
        subprocess.run(cmd_silent, capture_output=True, check=True)
        return out_path

    sfx_catalog = get_available_sfx()
    cmd = ["ffmpeg", "-y", "-hide_banner"]
    
    # Input 0: base silent anchor of exact duration
    cmd.extend([
        "-f", "lavfi",
        "-i", f"anullsrc=channel_layout=stereo:sample_rate=48000"
    ])

    filter_parts = ["[0:a]aformat=sample_rates=48000:channel_layouts=stereo[base]"]
    mix_labels = ["[base]"]

    valid_cues_count = 0
    for idx, cue in enumerate(cues):
        sfx_id = cue["sfx_id"]
        clip_info = sfx_catalog.get(sfx_id)
        if not clip_info:
            continue
        
        clip_file = SFX_CLIPS_DIR / f"{sfx_id}.mp3"
        if not clip_file.exists() and "file" in clip_info:
            clip_file = (ROOT / "media" / "library" / "sfx" / clip_info["file"]).resolve()

        if not clip_file.exists():
            continue

        valid_cues_count += 1
        cmd.extend(["-i", str(clip_file)])
        
        delay_ms = int(round(float(cue["at_s"]) * 1000.0))
        gain_db = float(cue.get("gain_db", -8.0))
        
        label = f"sfx{valid_cues_count}"
        filter_parts.append(
            f"[{valid_cues_count}:a]aformat=sample_rates=48000:channel_layouts=stereo,"
            f"adelay={delay_ms}:all=1,volume={gain_db:.2f}dB[{label}]"
        )
        mix_labels.append(f"[{label}]")

    if valid_cues_count == 0:
        # Nothing valid found, write silent
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-t", f"{total_dur:.3f}",
            "-c:a", "pcm_s16le",
            str(out_path)
        ], capture_output=True, check=True)
        return out_path

    # Mix inputs together
    all_inputs_str = "".join(mix_labels)
    filter_parts.append(f"{all_inputs_str}amix=inputs={len(mix_labels)}:normalize=0:dropout_transition=0[sfxraw]")
    filter_parts.append("[sfxraw]alimiter=level_in=1:level_out=1:limit=0.97[sfxbus]")

    cmd.extend([
        "-filter_complex", ";".join(filter_parts),
        "-map", "[sfxbus]",
        "-c:a", "pcm_s16le",
        "-ar", "48000",
        "-t", f"{total_dur:.3f}",
        str(out_path)
    ])

    print(f"[auto_sound_designer] Mixing {valid_cues_count} SFX cues into {out_path} ({total_dur:.1f}s)...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        sys.stderr.write(f"[auto_sound_designer] FFmpeg SFX bus mixing error:\n{res.stderr}\n")
        # Fallback to silent
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-t", f"{total_dur:.3f}",
            "-c:a", "pcm_s16le",
            str(out_path)
        ], capture_output=True)

    print(f"✓ SFX bus ready: {out_path}")
    return out_path


def design_and_render_sfx(beats_or_file, total_duration, out_wav_path):
    """Convenience helper: scores cues and renders SFX bus in one call."""
    beats_list = []
    if isinstance(beats_or_file, (str, Path)):
        p = Path(beats_or_file)
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    beats_list = data.get("scenes") or data.get("vo") or []
            except Exception:
                pass
    elif isinstance(beats_or_file, list):
        beats_list = beats_or_file

    cues = design_sfx_cues(beats_list, total_duration)
    return render_sfx_bus(cues, total_duration, out_wav_path)


def main():
    parser = argparse.ArgumentParser(description="Auto Sound Designer & SFX Scorer")
    parser.add_argument("--beats", help="Path to beats.json or scenes.json")
    parser.add_argument("--duration", type=float, help="Total duration in seconds")
    parser.add_argument("--out", help="Output SFX bus WAV file")
    parser.add_argument("--list", action="store_true", help="List available SFX clips")
    args = parser.parse_args()

    if args.list:
        sfx = get_available_sfx()
        print(f"Available Sound Effects ({len(sfx)}):")
        for k, v in sorted(sfx.items()):
            print(f"  • {k:<20} {v.get('category', 'sfx'):<15}")
        return

    if not args.out:
        parser.error("--out is required unless using --list")

    dur = args.duration
    if not dur and args.beats and Path(args.beats).exists():
        try:
            with open(args.beats, encoding="utf-8") as f:
                bdata = json.load(f)
                dur = float(bdata.get("format", {}).get("durationSec", 30.0))
        except Exception:
            dur = 30.0

    design_and_render_sfx(args.beats, dur or 30.0, args.out)


if __name__ == "__main__":
    main()
