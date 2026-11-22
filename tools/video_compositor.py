#!/usr/bin/env python3
"""
video_compositor.py — Universal Video, Voice & Captions Compositor.

Takes ANY video clip (from HunyuanVideo, FreeVideo, LongCat-Video, Seedance, or user upload),
layers Kokoro AI voice narration, kinetic yellow/white high-retention subtitles,
optional sound effects, and exports a 1080×1920 (9:16) viral YouTube Short.

Uses standard FFmpeg (pre-installed).
"""
import argparse
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent

def get_media_duration(file_path):
    """Returns duration in seconds using ffprobe."""
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

def format_ass_time(seconds):
    """Converts seconds into ASS timestamp H:MM:SS.cs"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds - int(seconds)) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def generate_ass_subtitles(beats_or_vo, out_ass_path):
    """Generates a viral-styled ASS subtitle file (TikTok / YouTube Shorts style)."""
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: ShortsDefault,Arial,64,&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,4,2,2,40,40,320,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for item in beats_or_vo:
        text = item.get("text", "").strip()
        if not text:
            continue
        start = float(item.get("start", 0))
        end = float(item.get("end", start + 3.0))
        
        # Split into punchy 4-6 word chunks so viewers can read effortlessly
        words = text.split()
        chunk_size = 5
        if len(words) <= chunk_size:
            start_str = format_ass_time(start)
            end_str = format_ass_time(end)
            events.append(f"Dialogue: 0,{start_str},{end_str},ShortsDefault,,0,0,0,,{text.upper()}")
        else:
            total_chunks = math.ceil(len(words) / chunk_size)
            chunk_dur = (end - start) / total_chunks
            for idx in range(total_chunks):
                sub_words = words[idx * chunk_size : (idx + 1) * chunk_size]
                c_start = start + idx * chunk_dur
                c_end = start + (idx + 1) * chunk_dur
                events.append(
                    f"Dialogue: 0,{format_ass_time(c_start)},{format_ass_time(c_end)},ShortsDefault,,0,0,0,,{' '.join(sub_words).upper()}"
                )

    out_ass_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_ass_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events) + "\n")

def composite_short(video_in, audio_in, beats_data, out_path, sfx_in=None):
    """
    Composites video + audio + subtitles into a 1080x1920 Short.
    """
    video_in = Path(video_in).resolve()
    audio_in = Path(audio_in).resolve() if audio_in else None
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    audio_dur = get_media_duration(audio_in) if audio_in and audio_in.exists() else 30.0
    video_dur = get_media_duration(video_in)

    # 1. Create Subtitle ASS
    ass_path = out_path.parent / "temp_captions.ass"
    generate_ass_subtitles(beats_data, ass_path)

    # Escaping for FFmpeg filter path on Windows
    ass_escaped = str(ass_path).replace("\\", "/").replace(":", "\\:")

    # 2. Build FFmpeg command
    # Scale & crop to 1080x1920 9:16 vertical + burn subtitles
    filter_graph = f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,subtitles='{ass_escaped}'[v]"

    cmd = ["ffmpeg", "-y"]

    # Loop video if shorter than audio
    if video_dur < audio_dur:
        cmd.extend(["-stream_loop", "-1"])

    cmd.extend(["-i", str(video_in)])

    # Add audio inputs
    if audio_in and audio_in.exists():
        cmd.extend(["-i", str(audio_in)])
        if sfx_in and Path(sfx_in).exists():
            cmd.extend(["-i", str(sfx_in)])
            filter_graph += ";[1:a][2:a]amix=inputs=2:duration=first:dropout_transition=2[a]"
            audio_map = "[a]"
        else:
            audio_map = "1:a"
    else:
        audio_map = "0:a"

    cmd.extend([
        "-filter_complex", filter_graph,
        "-map", "[v]",
        "-map", audio_map,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "192k",
        "-t", str(audio_dur + 0.5),
        "-shortest",
        str(out_path)
    ])

    print(f"Compositing short: {out_path}...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0 and out_path.exists():
        print(f"✓ Final Short ready: {out_path}")
        return True
    else:
        print(f"FFmpeg compositing error:\n{res.stderr}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Universal Video Compositor")
    parser.add_argument("--video", required=True, help="Input video MP4")
    parser.add_argument("--audio", required=True, help="Voiceover audio WAV/MP3")
    parser.add_argument("--beats", required=True, help="beats.json or text script")
    parser.add_argument("--out", required=True, help="Output MP4")
    parser.add_argument("--sfx", help="Optional SFX track")
    args = parser.parse_args()

    beats_data = []
    p_beats = Path(args.beats)
    if p_beats.exists():
        try:
            with open(p_beats, encoding="utf-8") as f:
                b_json = json.load(f)
                beats_data = b_json.get("vo", [])
        except Exception:
            pass

    success = composite_short(args.video, args.audio, beats_data, args.out, args.sfx)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
