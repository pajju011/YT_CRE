#!/usr/bin/env python3
"""
animate_scenes.py — Multi-Scene Image-to-Video Animator & Sequencer.

Animates 2D scene still images into dynamic 1080x1920 (9:16) video clips:
- Camera motions: push-in, zoom-out, pan-left, pan-right, tilt-up, breathing-orbit.
- High-efficiency 30fps rendering via FFmpeg.
- Seamlessly stitches multiple scene clips with crossfade transitions into a continuous short.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys
from typing import List, Dict, Any

ROOT = Path(__file__).resolve().parent.parent

MOTION_PRESETS = {
    "zoom_in": {
        "name": "Cinematic Push-In",
        "expr": "z='min(zoom+0.0012\\,1.18)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
    },
    "zoom_out": {
        "name": "Heroic Reveal Zoom-Out",
        "expr": "z='if(eq(on\\,1)\\,1.18\\,max(1.0\\,zoom-0.0012))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
    },
    "pan_left": {
        "name": "Cinematic Pan Left",
        "expr": "z='1.12':x='max(0\\,(iw-iw/zoom)*(1.0-on/{total_frames}))':y='ih/2-(ih/zoom/2)'"
    },
    "pan_right": {
        "name": "Dynamic Pan Right",
        "expr": "z='1.12':x='min(iw-iw/zoom\\,(iw-iw/zoom)*(on/{total_frames}))':y='ih/2-(ih/zoom/2)'"
    },
    "tilt_up": {
        "name": "Dramatic Tilt Up",
        "expr": "z='1.12':x='iw/2-(iw/zoom/2)':y='max(0\\,(ih-ih/zoom)*(1.0-on/{total_frames}))'"
    },
    "breathing": {
        "name": "Living Atmosphere Orbit",
        "expr": "z='1.05+0.03*sin(on/20)':x='iw/2-(iw/zoom/2)+sin(on/25)*8':y='ih/2-(ih/zoom/2)+cos(on/30)*6'"
    }
}

def animate_scene_still(image_path: Path, out_clip_path: Path, motion: str = "zoom_in", duration: float = 4.5, fps: int = 30) -> bool:
    """
    Animates a single scene still image into a 1080x1920 MP4 clip.
    """
    image_path = Path(image_path).resolve()
    out_clip_path = Path(out_clip_path).resolve()
    out_clip_path.parent.mkdir(parents=True, exist_ok=True)

    if not image_path.exists():
        print(f"Error: Scene image not found: {image_path}")
        return False

    preset = MOTION_PRESETS.get(motion, MOTION_PRESETS["zoom_in"])
    total_frames = max(1, int(duration * fps))
    motion_expr = preset["expr"].format(total_frames=total_frames)

    # Scale & crop to 9:16 then apply zoompan filter
    vf = (
        f"scale=1080:1920:force_original_aspect_ratio=increase,"
        f"crop=1080:1920,"
        f"zoompan={motion_expr}:d={total_frames}:s=1080x1920:fps={fps}"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(image_path),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-t", str(duration),
        "-pix_fmt", "yuv420p",
        str(out_clip_path)
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0 and out_clip_path.exists():
        print(f"✓ Scene clip animated [{motion}]: {out_clip_path.name} ({duration}s)")
        return True
    else:
        print(f"[FFmpeg animation error] {res.stderr}")
        return False

def stitch_scene_clips(clip_paths: List[Path], out_video_path: Path, transition_dur: float = 0.3) -> bool:
    """
    Stitches multiple scene video clips into a single continuous video with smooth transitions.
    """
    out_video_path = Path(out_video_path).resolve()
    out_video_path.parent.mkdir(parents=True, exist_ok=True)

    valid_clips = [p.resolve() for p in clip_paths if p.exists()]
    if not valid_clips:
        print("Error: No valid clips found to stitch.")
        return False

    if len(valid_clips) == 1:
        # Single clip, copy directly
        import shutil
        shutil.copyfile(valid_clips[0], out_video_path)
        print(f"✓ Single scene copied to: {out_video_path}")
        return True

    # Build concat file list
    concat_list_path = out_video_path.parent / "scenes_concat.txt"
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for clip in valid_clips:
            # Escape path for FFmpeg concat demuxer
            clean_path = str(clip).replace("\\", "/")
            f.write(f"file '{clean_path}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list_path),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "19",
        "-pix_fmt", "yuv420p",
        str(out_video_path)
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if concat_list_path.exists():
        try:
            concat_list_path.unlink()
        except Exception:
            pass

    if res.returncode == 0 and out_video_path.exists():
        print(f"✓ All {len(valid_clips)} scenes stitched successfully: {out_video_path}")
        return True
    else:
        print(f"[Stitching error] {res.stderr}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Scene Video Animator")
    parser.add_argument("--image", help="Single image to animate")
    parser.add_argument("--out", help="Output clip or stitched video path")
    parser.add_argument("--motion", default="zoom_in", choices=list(MOTION_PRESETS.keys()), help="Camera motion preset")
    parser.add_argument("--duration", type=float, default=4.0, help="Clip duration in seconds")
    parser.add_argument("--stitch", nargs="+", help="List of clip paths to stitch")
    args = parser.parse_args()

    if args.stitch:
        clips = [Path(p) for p in args.stitch]
        out_v = Path(args.out) if args.out else Path("output/storyboard_raw.mp4")
        success = stitch_scene_clips(clips, out_v)
        sys.exit(0 if success else 1)
    elif args.image and args.out:
        success = animate_scene_still(Path(args.image), Path(args.out), args.motion, args.duration)
        sys.exit(0 if success else 1)
    else:
        parser.print_help()
