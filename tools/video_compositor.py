#!/usr/bin/env python3
"""
video_compositor.py — Universal Video, Voice, Music & Captions Compositor.

Takes ANY video clip (from HunyuanVideo, FreeVideo, LongCat-Video, Seedance, Storyboard,
Talking Avatar, or user upload), layers:
1. Spoken voiceover (Kokoro / Edge-TTS multilingual)
2. Auto-sound design (SFX bus placed at narrative beat transitions)
3. Background music bed (ducked under speech with sidechain compression)
4. Kinetic yellow/white high-retention subtitles (ASS TikTok/Shorts style)
and exports a broadcast-quality 1080×1920 (9:16) viral YouTube Short.

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

# Import audio engine modules
try:
    from tools.audio_ducker import mix_voice_and_music
    from tools.auto_sound_designer import design_and_render_sfx
except ImportError:
    sys.path.insert(0, str(ROOT))
    from tools.audio_ducker import mix_voice_and_music
    from tools.auto_sound_designer import design_and_render_sfx


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
        text = item.get("text", "") or item.get("narration", "")
        text = text.strip()
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


def prepare_master_audio(audio_in, beats_data, work_dir, music_bed="lofi-warm", sfx_enabled=True, sfx_file=None):
    """
    Masters the audio pass:
    Voice + Auto-SFX + Ducked Music Bed -> single clean 48kHz stereo WAV.
    """
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    audio_path = Path(audio_in).resolve() if audio_in else None

    if not audio_path or not audio_path.exists():
        return None, 30.0

    voice_dur = get_media_duration(audio_path)
    total_dur = voice_dur + 0.3

    current_voice_stem = audio_path

    # Step 1: Render and layer SFX bus if enabled
    if sfx_enabled:
        sfx_bus_path = work_dir / "temp_sfx_bus.wav"
        if sfx_file and Path(sfx_file).exists():
            sfx_bus_path = Path(sfx_file).resolve()
        else:
            print(f"[video_compositor] Scoring auto-SFX bus for {len(beats_data)} beats...")
            design_and_render_sfx(beats_data, total_dur, sfx_bus_path)

        if sfx_bus_path.exists():
            voice_sfx_path = work_dir / "temp_voice_sfx.wav"
            cmd_mix_sfx = [
                "ffmpeg", "-y", "-hide_banner",
                "-i", str(current_voice_stem),
                "-i", str(sfx_bus_path),
                "-filter_complex",
                "[0:a]aformat=sample_rates=48000:channel_layouts=stereo[a0];"
                "[1:a]aformat=sample_rates=48000:channel_layouts=stereo[a1];"
                "[a0][a1]amix=inputs=2:normalize=0:dropout_transition=0[mix];"
                "[mix]alimiter=level_in=1:level_out=1:limit=0.97[outa]",
                "-map", "[outa]",
                "-c:a", "pcm_s16le",
                "-t", f"{total_dur:.3f}",
                str(voice_sfx_path)
            ]
            res_sfx = subprocess.run(cmd_mix_sfx, capture_output=True, text=True)
            if res_sfx.returncode == 0 and voice_sfx_path.exists():
                current_voice_stem = voice_sfx_path

    # Step 2: Layer ducked background music bed if enabled
    if music_bed and str(music_bed).lower() not in ["none", "off", "disabled"]:
        master_audio_path = work_dir / f"temp_master_{music_bed}.wav"
        print(f"[video_compositor] Applying sidechain ducking for music bed '{music_bed}'...")
        try:
            mix_voice_and_music(
                current_voice_stem,
                music_bed,
                master_audio_path,
                bed_gain_db=-12.0,
                duck_db=10.0,
                fade_sec=1.5
            )
            if master_audio_path.exists():
                return master_audio_path, total_dur
        except Exception as e:
            sys.stderr.write(f"[video_compositor] Music ducking error: {e}\n")

    return current_voice_stem, total_dur


def composite_short(video_in, audio_in, beats_data, out_path, music_bed="lofi-warm", sfx_enabled=True, sfx_in=None):
    """
    Composites video + voice + ducked music + SFX + subtitles into a 1080x1920 Short.
    """
    video_in = Path(video_in).resolve()
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    work_dir = out_path.parent

    # 1. Master Audio Pass (Voice + SFX + Ducked Music)
    master_audio, audio_dur = prepare_master_audio(
        audio_in,
        beats_data,
        work_dir,
        music_bed=music_bed,
        sfx_enabled=sfx_enabled,
        sfx_file=sfx_in
    )

    video_dur = get_media_duration(video_in)

    # 2. Create Subtitle ASS
    ass_path = work_dir / "temp_captions.ass"
    generate_ass_subtitles(beats_data, ass_path)

    # Escaping for FFmpeg filter path on Windows
    ass_escaped = str(ass_path).replace("\\", "/").replace(":", "\\:")

    # 3. Build FFmpeg command
    filter_graph = f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,subtitles='{ass_escaped}'[v]"

    cmd = ["ffmpeg", "-y", "-hide_banner"]

    # Loop video if shorter than audio
    if video_dur < audio_dur:
        cmd.extend(["-stream_loop", "-1"])

    cmd.extend(["-i", str(video_in)])

    # Add master audio input
    if master_audio and master_audio.exists():
        cmd.extend(["-i", str(master_audio)])
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
        "-t", str(audio_dur + 0.3),
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
    parser.add_argument("--music", default="lofi-warm", help="Background music bed (e.g. lofi-warm, ambient-pad, none)")
    parser.add_argument("--sfx", action="store_true", default=True, help="Enable auto sound effects")
    parser.add_argument("--no-sfx", dest="sfx", action="store_false", help="Disable auto sound effects")
    parser.add_argument("--sfx-file", help="Optional pre-rendered SFX audio track")
    args = parser.parse_args()

    beats_data = []
    p_beats = Path(args.beats)
    if p_beats.exists():
        try:
            with open(p_beats, encoding="utf-8") as f:
                b_json = json.load(f)
                beats_data = b_json.get("scenes") or b_json.get("vo") or []
        except Exception:
            pass

    success = composite_short(
        args.video,
        args.audio,
        beats_data,
        args.out,
        music_bed=args.music,
        sfx_enabled=args.sfx,
        sfx_in=args.sfx_file
    )
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
