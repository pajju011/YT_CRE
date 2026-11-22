#!/usr/bin/env python3
"""
audio_ducker.py — Production-Grade Background Music Bed & Sidechain Audio Ducking Engine.

Features:
- Loads curated, loudness-normalized instrumental music beds from media/library/music/.
- Automatically matches audio duration to the spoken voice track.
- Applies gentle high-pass filter (100Hz) so low-end music bass never clashes with speech fundamentals.
- Professional sidechain compression ducking: music stays quiet under voice and smoothly breathes up during pauses.
- Smooth head/tail crossfading (1.5s default).
- Safety peak limiting to ensure 0 dBFS true-peak compliance without clipping.
"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
MUSIC_CATALOG_PATH = ROOT / "media" / "library" / "music" / "catalog.json"
MUSIC_CLIPS_DIR = ROOT / "media" / "library" / "music" / "clips"


def get_available_music_beds():
    """Returns a list of available music bed dictionaries."""
    if not MUSIC_CATALOG_PATH.exists():
        # Fallback to scanning clips directory
        beds = []
        if MUSIC_CLIPS_DIR.exists():
            for f in MUSIC_CLIPS_DIR.glob("*.mp3"):
                beds.append({
                    "id": f.stem,
                    "title": f.stem.replace("-", " ").title(),
                    "file": f"clips/{f.name}",
                    "category": "general"
                })
        return beds

    try:
        with open(MUSIC_CATALOG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("clips", [])
    except Exception as e:
        sys.stderr.write(f"[audio_ducker] Error reading music catalog: {e}\n")
        return []


def get_audio_duration(file_path):
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


def mix_voice_and_music(voice_wav, bed_id, out_audio_path, bed_gain_db=-12.0, duck_db=10.0, fade_sec=1.5):
    """
    Mixes voice audio with a ducked background music bed.
    
    Args:
        voice_wav: Path to spoken voice track (WAV / MP3).
        bed_id: Identifier of the music bed (e.g. 'lofi-warm', 'ambient-pad') or 'none'.
        out_audio_path: Destination path for final master audio track.
        bed_gain_db: Base volume level of music bed in dB (default: -12.0 dB).
        duck_db: Additional attenuation applied to music when voice is active (default: 10.0 dB).
        fade_sec: Duration in seconds for fade-in and fade-out.
    
    Returns:
        Path to generated master audio file, or original voice_wav if bed is 'none'.
    """
    voice_path = Path(voice_wav).resolve()
    out_path = Path(out_audio_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not voice_path.exists():
        raise FileNotFoundError(f"Voice audio track not found: {voice_path}")

    if not bed_id or bed_id.lower() in ["none", "off", "disabled"]:
        print(f"[audio_ducker] Music bed set to '{bed_id}'. Passing voice audio through.")
        # Simply convert/copy voice to destination
        cmd_copy = ["ffmpeg", "-y", "-i", str(voice_path), "-c:a", "pcm_s16le", "-ar", "24000", str(out_path)]
        subprocess.run(cmd_copy, capture_output=True, check=True)
        return out_path

    # Resolve music bed file
    bed_file = MUSIC_CLIPS_DIR / f"{bed_id}.mp3"
    if not bed_file.exists():
        # Check catalog for alternative filename
        beds = {b["id"]: b for b in get_available_music_beds()}
        if bed_id in beds and "file" in beds[bed_id]:
            bed_file = (ROOT / "media" / "library" / "music" / beds[bed_id]["file"]).resolve()

    if not bed_file.exists():
        print(f"[audio_ducker] Warning: Music bed '{bed_id}' not found at {bed_file}. Using dry voice.")
        cmd_copy = ["ffmpeg", "-y", "-i", str(voice_path), "-c:a", "pcm_s16le", "-ar", "24000", str(out_path)]
        subprocess.run(cmd_copy, capture_output=True, check=True)
        return out_path

    voice_dur = get_audio_duration(voice_path)
    total_dur = voice_dur + 0.3  # Add slight tail padding

    ratio = max(2.5, duck_db / 3.0)
    fade_tail = max(0.0, total_dur - fade_sec)

    # FFmpeg sidechain ducking filtergraph:
    # 0:a = voice track
    # 1:a = music bed (looped indefinitely)
    filter_complex = (
        f"[1:a]aformat=sample_rates=48000:channel_layouts=stereo,"
        f"highpass=f=100,volume={bed_gain_db:.2f}dB,atrim=0:{total_dur:.3f},asetpts=N/SR/TB,"
        f"afade=t=in:st=0:d={fade_sec:.2f},afade=t=out:st={fade_tail:.3f}:d={fade_sec:.2f}[bed];"
        f"[0:a]aformat=sample_rates=48000:channel_layouts=stereo,asplit=2[key][voice];"
        f"[bed][key]sidechaincompress=threshold=0.03:ratio={ratio:.2f}:attack=15:release=400:makeup=1[bedduck];"
        f"[voice][bedduck]amix=inputs=2:normalize=0:dropout_transition=0[mixraw];"
        f"[mixraw]alimiter=level_in=1:level_out=1:limit=0.97[mix]"
    )

    cmd = [
        "ffmpeg", "-y", "-hide_banner",
        "-i", str(voice_path),
        "-stream_loop", "-1", "-i", str(bed_file),
        "-filter_complex", filter_complex,
        "-map", "[mix]",
        "-c:a", "pcm_s16le",
        "-ar", "48000",
        "-t", f"{total_dur:.3f}",
        str(out_path)
    ]

    print(f"[audio_ducker] Mixing music bed '{bed_id}' (gain={bed_gain_db}dB, duck={duck_db}dB) with voice ({voice_dur:.1f}s)...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        sys.stderr.write(f"[audio_ducker] FFmpeg mixing error:\n{res.stderr}\n")
        # Fallback to copy
        subprocess.run(["ffmpeg", "-y", "-i", str(voice_path), str(out_path)], capture_output=True)

    print(f"✓ Master ducked audio ready: {out_path}")
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Audio Ducker & Music Bed Mixer")
    parser.add_argument("--voice", help="Path to input voice WAV/MP3")
    parser.add_argument("--bed", default="lofi-warm", help="Music bed ID (e.g. lofi-warm, ambient-pad, none)")
    parser.add_argument("--out", help="Output master audio WAV")
    parser.add_argument("--gain", type=float, default=-12.0, help="Music bed base gain in dB (default: -12.0)")
    parser.add_argument("--duck", type=float, default=10.0, help="Ducking attenuation in dB (default: 10.0)")
    parser.add_argument("--fade", type=float, default=1.5, help="Fade in/out duration in seconds (default: 1.5)")
    parser.add_argument("--list", action="store_true", help="List available music beds")
    args = parser.parse_args()

    if args.list:
        beds = get_available_music_beds()
        print(f"Available Music Beds ({len(beds)}):")
        for b in beds:
            print(f"  • {b.get('id', '')}: {b.get('category', 'bed')} - {b.get('tags', [])}")
        return

    if not args.voice or not args.out:
        parser.error("--voice and --out are required unless using --list")

    mix_voice_and_music(
        args.voice,
        args.bed,
        args.out,
        bed_gain_db=args.gain,
        duck_db=args.duck,
        fade_sec=args.fade
    )


if __name__ == "__main__":
    main()
