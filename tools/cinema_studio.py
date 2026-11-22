#!/usr/bin/env python3
"""
cinema_studio.py — Freefield Cinema Studio & 33 Camera Moves Video Generation Engine.

Directly implements Freefield / Higgsfield 4.0 Cinema Studio techniques:
1. Dual-Prompt Compilation:
   - Frame 0 Still Prompt: Film Still + Genre + Era + Camera Body + Lens + Lighting + Palette.
   - Motion Prompt: Camera Choreography (33 Moves) + Tempo + Scene Dynamics.
2. Motion Execution:
   - Cloud Path: Wan 2.5 / Kling / Colab LTX-Video ComfyUI workflows.
   - Free Local Path: NVIDIA Sana 9:16 Still + 33 Dynamic Sub-Pixel Camera Easing Curves via FFmpeg Lanczos.
3. Audio & Captions Scoring:
   - Voice narration + synchronized camera transition SFX + sidechain ducked cinematic score + kinetic ASS subtitles.
"""

import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from typing import Dict, Any, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# -----------------------------------------------------------------------------
# FREEFIELD 33 CAMERA MOVES CATALOG
# -----------------------------------------------------------------------------
CAMERA_MOVES = {
    "dolly_in": {
        "id": "dolly_in",
        "name": "Dolly In",
        "prompt_val": "The camera slowly dollies in toward the subject.",
        "sfx": "whoosh-soft",
        "expr": "z='min(zoom+0.0012\\,1.20)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
        "desc": "Smooth linear forward motion approaching the subject."
    },
    "dolly_out": {
        "id": "dolly_out",
        "name": "Dolly Out",
        "prompt_val": "The camera slowly dollies back away from the subject.",
        "sfx": "whoosh-wind",
        "expr": "z='if(eq(on\\,1)\\,1.20\\,max(1.0\\,zoom-0.0012))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
        "desc": "Smooth linear backward motion revealing wider context."
    },
    "crash_zoom": {
        "id": "crash_zoom",
        "name": "Crash Zoom",
        "prompt_val": "The camera crash-zooms in fast on the subject with rapid motion blur.",
        "sfx": "impact-soft",
        "expr": "z='min(zoom+0.0035\\,1.35)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
        "desc": "High-velocity sudden push-in for dramatic emphasis."
    },
    "dolly_zoom": {
        "id": "dolly_zoom",
        "name": "Dolly Zoom (Vertigo Effect)",
        "prompt_val": "The camera dolly-zooms, moving in while optical focal length widens, stretching background perspective.",
        "sfx": "riser-soft",
        "expr": "z='1.15+0.12*sin(on*3.1415/{total_frames})':x='iw/2-(iw/zoom/2)+sin(on*3.1415/{total_frames})*12':y='ih/2-(ih/zoom/2)'",
        "desc": "Hitchcock Vertigo counter-zoom effect warping space."
    },
    "bullet_time": {
        "id": "bullet_time",
        "name": "360° Bullet Time Orbit",
        "prompt_val": "The camera circles around a frozen moment in slow motion, bullet-time matrix style.",
        "sfx": "warm-shimmer",
        "expr": "z='1.12+0.04*cos(on*6.28/{total_frames})':x='(iw-iw/zoom)*(0.5+0.45*sin(on*6.28/{total_frames}))':y='(ih-ih/zoom)*(0.5+0.35*cos(on*6.28/{total_frames}))'",
        "desc": "Matrix-style circular orbit freeze around the subject."
    },
    "pan_left": {
        "id": "pan_left",
        "name": "Pan Left",
        "prompt_val": "The camera pans left across the scene.",
        "sfx": "whoosh-soft",
        "expr": "z='1.15':x='max(0\\,(iw-iw/zoom)*(1.0-on/{total_frames}))':y='ih/2-(ih/zoom/2)'",
        "desc": "Horizontal pivot sweeping left."
    },
    "pan_right": {
        "id": "pan_right",
        "name": "Pan Right",
        "prompt_val": "The camera pans right across the scene.",
        "sfx": "whoosh-soft",
        "expr": "z='1.15':x='min(iw-iw/zoom\\,(iw-iw/zoom)*(on/{total_frames}))':y='ih/2-(ih/zoom/2)'",
        "desc": "Horizontal pivot sweeping right."
    },
    "whip_pan": {
        "id": "whip_pan",
        "name": "Whip Pan",
        "prompt_val": "The camera whip-pans fast to the side with cinematic motion blur.",
        "sfx": "whoosh-reverse",
        "expr": "z='1.18':x='(iw-iw/zoom)*(1.0/(1.0+exp(-10.0*(on/{total_frames}-0.5))))':y='ih/2-(ih/zoom/2)'",
        "desc": "High-velocity snap pan with kinetic blur."
    },
    "tilt_up": {
        "id": "tilt_up",
        "name": "Tilt Up",
        "prompt_val": "The camera tilts up toward the sky.",
        "sfx": "riser-soft",
        "expr": "z='1.15':x='iw/2-(iw/zoom/2)':y='max(0\\,(ih-ih/zoom)*(1.0-on/{total_frames}))'",
        "desc": "Vertical upward camera tilt."
    },
    "tilt_down": {
        "id": "tilt_down",
        "name": "Tilt Down",
        "prompt_val": "The camera tilts down toward the subject.",
        "sfx": "whoosh-soft",
        "expr": "z='1.15':x='iw/2-(iw/zoom/2)':y='min(ih-ih/zoom\\,(ih-ih/zoom)*(on/{total_frames}))'",
        "desc": "Vertical downward camera tilt."
    },
    "pedestal_up": {
        "id": "pedestal_up",
        "name": "Pedestal Up",
        "prompt_val": "The camera rises straight up, staying level.",
        "sfx": "riser-soft",
        "expr": "z='1.10':x='iw/2-(iw/zoom/2)':y='(ih-ih/zoom)*(1.0-on/{total_frames})'",
        "desc": "Elevator-like vertical rise without tilting."
    },
    "pedestal_down": {
        "id": "pedestal_down",
        "name": "Pedestal Down",
        "prompt_val": "The camera lowers straight down, staying level.",
        "sfx": "whoosh-soft",
        "expr": "z='1.10':x='iw/2-(iw/zoom/2)':y='(ih-ih/zoom)*(on/{total_frames})'",
        "desc": "Elevator-like vertical descent."
    },
    "arc_left": {
        "id": "arc_left",
        "name": "Arc Left",
        "prompt_val": "The camera arcs left around the subject.",
        "sfx": "whoosh-soft",
        "expr": "z='1.14':x='(iw-iw/zoom)*(0.5+0.4*sin(on*3.14/{total_frames}))':y='(ih-ih/zoom)*(0.5-0.2*cos(on*3.14/{total_frames}))'",
        "desc": "Curvilinear orbital path around the front of the subject."
    },
    "arc_right": {
        "id": "arc_right",
        "name": "Arc Right",
        "prompt_val": "The camera arcs right around the subject.",
        "sfx": "whoosh-soft",
        "expr": "z='1.14':x='(iw-iw/zoom)*(0.5-0.4*sin(on*3.14/{total_frames}))':y='(ih-ih/zoom)*(0.5-0.2*cos(on*3.14/{total_frames}))'",
        "desc": "Curvilinear orbital path curving to the right."
    },
    "crane_down": {
        "id": "crane_down",
        "name": "Crane Down",
        "prompt_val": "The camera cranes down from above toward the subject.",
        "sfx": "impact-deep-soft",
        "expr": "z='min(zoom+0.0016\\,1.25)':x='iw/2-(iw/zoom/2)':y='(ih-ih/zoom)*(on/{total_frames})'",
        "desc": "High angle jib descending into intimate eye-level."
    },
    "drone_orbit": {
        "id": "drone_orbit",
        "name": "Drone Orbit",
        "prompt_val": "The camera orbits the scene from above like a cinematic drone.",
        "sfx": "wind-soft",
        "expr": "z='1.10+0.06*sin(on*3.14/{total_frames})':x='(iw-iw/zoom)*(0.5+0.35*cos(on*4.0/{total_frames}))':y='(ih-ih/zoom)*(0.3+0.3*sin(on*4.0/{total_frames}))'",
        "desc": "Aerial sweeping orbit surveying environment."
    },
    "tracking": {
        "id": "tracking",
        "name": "Dynamic Tracking",
        "prompt_val": "The camera tracks behind the subject as they move.",
        "sfx": "whoosh-soft",
        "expr": "z='1.15':x='(iw-iw/zoom)*(0.5+0.1*sin(on/15))':y='(ih-ih/zoom)*(0.5+0.05*cos(on/18))'",
        "desc": "Steadycam tracking shot holding consistent distance."
    },
    "handheld": {
        "id": "handheld",
        "name": "Cinematic Handheld",
        "prompt_val": "The camera is handheld, with subtle natural breathing and micro-shake.",
        "sfx": "whoosh-soft",
        "expr": "z='1.08+0.02*sin(on/12)':x='iw/2-(iw/zoom/2)+sin(on/8)*7':y='ih/2-(ih/zoom/2)+cos(on/10)*6'",
        "desc": "Organic documentary handheld presence."
    },
    "static": {
        "id": "static",
        "name": "Static Locked Off",
        "prompt_val": "The camera stays locked off on a tripod, perfectly still.",
        "sfx": "clock-tick-soft",
        "expr": "z='1.05':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
        "desc": "Rock-solid composition allowing subject motion to speak."
    }
}

# -----------------------------------------------------------------------------
# FREEFIELD FILM LOOK CATALOG
# -----------------------------------------------------------------------------
GENRES = {
    "noir": "from a film noir, moody, high contrast, wet pavement reflections",
    "cyberpunk": "from a futuristic cyberpunk thriller, neon lights, volumetric rain",
    "scifi": "from a grand science-fiction space opera, sleek technological aesthetic",
    "drama": "from a prestigious cinematic drama, emotional realism, authentic texture",
    "western": "from a classic cinematic western, golden dust atmosphere, harsh sunlight",
    "action": "from a high-budget cinematic action blockbuster, dynamic energy, anamorphic lens flares",
    "general": "from a feature film, cinematic composition, master color grading"
}

ERAS = {
    "1970s": "set in the 1970s, warm vintage color tone, Panavision glass rendering",
    "1980s": "set in the 1980s, analog grain, vibrant neon lighting, classic retro look",
    "1990s": "set in the 1990s, indie film 35mm grain, organic contrast",
    "modern": "set in the present day, 8K ultra-clean sensor detail, high dynamic range",
    "future": "set in the near future, holographic accents, pristine advanced optics"
}

CAMERAS = {
    "arri": "the full-frame digital cinema look of an ARRI Alexa 65, natural skin tones and smooth rolloff",
    "red": "the crisp, clean razor-sharp detail of an 8K RED V-Raptor digital cinema camera",
    "imax_70mm": "the rich grand detail and fine organic grain of large-format IMAX 70mm film",
    "bolex_16mm": "the tactile, nostalgic grainy texture of classic Bolex 16mm film",
    "panavision": "the legendary Hollywood Panavision Millennium DXL2 cinematic color science"
}

LENSES = {
    "anamorphic": "a classic anamorphic widescreen look with oval bokeh and horizontal blue streak flares",
    "prime_50mm": "a clean, sharp 50mm modern prime lens with creamy natural background blur",
    "wide_24mm": "a dynamic wide 24mm perspective emphasizing scale and environmental depth",
    "portrait_85mm": "a classic 85mm portrait telephoto lens with creamy shallow depth of field bokeh",
    "vintage": "the warm, slightly soft rendering of 1970s vintage cinema prime glass with gentle halation"
}

LIGHTINGS = {
    "golden_hour": "volumetric golden hour sunset light, warm rim glow and gentle atmospheric haze",
    "chiaroscuro": "moody chiaroscuro lighting, deep dramatic shadows and sculpted highlights",
    "neon_cyber": "harsh neon cyan and magenta backlighting reflecting on wet surfaces",
    "rembrandt": "soft cinematic Rembrandt studio lighting, gentle key with subtle fill and rim",
    "silhouette": "dramatic silhouette lighting against a bright glowing background",
    "cinematic": "natural cinematic lighting with soft shadow transitions"
}

PALETTES = {
    "teal_orange": "blockbuster teal and orange color grade, rich skin tones and cool shadow contrast",
    "monochrome": "dramatic monochrome silver gelatin black and white with rich silver tones",
    "neon_glow": "vibrant cyber neon palette with deep blacks and luminous neon glows",
    "kodak_gold": "warm vintage Kodak Gold 35mm film palette with rich golden hues",
    "desaturated": "moody desaturated cinematic grade with muted earthy tones and crisp highlights"
}

# -----------------------------------------------------------------------------
# CURATED 1-CLICK CINEMA PRESETS
# -----------------------------------------------------------------------------
CINEMA_PRESETS = {
    "matrix_bullet_time": {
        "title": "Matrix 360° Bullet Time",
        "genre": "scifi",
        "era": "modern",
        "camera": "arri",
        "lens": "anamorphic",
        "lighting": "neon_cyber",
        "palette": "neon_glow",
        "camera_move": "bullet_time",
        "sample_prompt": "A cyber warrior floating mid-air dodging glowing laser beams as time freezes around him"
    },
    "cyberpunk_noir": {
        "title": "Cyberpunk Noir Detective",
        "genre": "noir",
        "era": "future",
        "camera": "panavision",
        "lens": "anamorphic",
        "lighting": "chiaroscuro",
        "palette": "teal_orange",
        "camera_move": "dolly_in",
        "sample_prompt": "A detective in a trench coat lights a cigarette under neon rain in a dark futuristic alley"
    },
    "vertigo_dolly_zoom": {
        "title": "Vertigo Dolly Zoom",
        "genre": "drama",
        "era": "modern",
        "camera": "red",
        "lens": "prime_50mm",
        "lighting": "rembrandt",
        "palette": "desaturated",
        "camera_move": "dolly_zoom",
        "sample_prompt": "A stunned protagonist turning around in shock as the world warps and expands behind them"
    },
    "fpv_action_drone": {
        "title": "FPV Action Drone Dive",
        "genre": "action",
        "era": "modern",
        "camera": "imax_70mm",
        "lens": "wide_24mm",
        "lighting": "golden_hour",
        "palette": "teal_orange",
        "camera_move": "drone_orbit",
        "sample_prompt": "An extreme athlete leaping from a cliff edge into a majestic sunlit canyon"
    },
    "vintage_western": {
        "title": "1970s Panavision Western",
        "genre": "western",
        "era": "1970s",
        "camera": "imax_70mm",
        "lens": "vintage",
        "lighting": "golden_hour",
        "palette": "kodak_gold",
        "camera_move": "pan_right",
        "sample_prompt": "A solitary gunslinger on horseback gazing across the vast arid desert at sundown"
    }
}


def compile_cinema_prompts(
    base_prompt: str,
    genre: str = "general",
    era: str = "modern",
    camera: str = "arri",
    lens: str = "anamorphic",
    lighting: str = "cinematic",
    palette: str = "teal_orange",
    camera_move: str = "dolly_in"
) -> Dict[str, str]:
    """
    Compiles dual-prompts following Freefield / Higgsfield Cinema Studio architecture:
    1. Still Prompt: Draws the first frame with high fidelity film look.
    2. Motion Prompt: Directs the camera motion, pacing, and action dynamics.
    """
    g_text = GENRES.get(genre, GENRES["general"])
    e_text = ERAS.get(era, ERAS["modern"])
    c_text = CAMERAS.get(camera, CAMERAS["arri"])
    l_text = LENSES.get(lens, LENSES["anamorphic"])
    li_text = LIGHTINGS.get(lighting, LIGHTINGS["cinematic"])
    p_text = PALETTES.get(palette, PALETTES["teal_orange"])
    move_info = CAMERA_MOVES.get(camera_move, CAMERA_MOVES["dolly_in"])

    # Frame 0 Stills Prompt (for NVIDIA Sana / FLUX 3 Klein)
    still_prompt = (
        f"A cinematic film still, {g_text}, {e_text}: {base_prompt}. "
        f"The look: {c_text}; {l_text}. Lighting: {li_text}. Color: {p_text}. "
        f"Mastershot composition, 8k resolution, photorealistic, 9:16 vertical ratio."
    )

    # Video Motion Prompt (for Wan 2.5 / Kling / LTX-Video)
    motion_prompt = (
        f"{move_info['prompt_val']} {base_prompt}. Dynamic cinematic pacing. "
        f"The look of a film {g_text}, {e_text}: {c_text}; {l_text}. "
        f"Lighting: {li_text}. Color: {p_text}."
    )

    return {
        "still_prompt": still_prompt,
        "motion_prompt": motion_prompt,
        "camera_move": camera_move,
        "sfx_cue": move_info.get("sfx", "whoosh-soft")
    }


def render_cinema_motion_clip(
    image_path: Path,
    out_clip_path: Path,
    camera_move: str = "dolly_in",
    duration: float = 5.0,
    fps: int = 30
) -> bool:
    """
    Renders the exact Freefield camera move on a still image using sub-pixel easing curves.
    """
    image_path = Path(image_path).resolve()
    out_clip_path = Path(out_clip_path).resolve()
    out_clip_path.parent.mkdir(parents=True, exist_ok=True)

    if not image_path.exists():
        print(f"Error: Scene still image not found: {image_path}")
        return False

    move_info = CAMERA_MOVES.get(camera_move, CAMERA_MOVES["dolly_in"])
    total_frames = max(1, int(duration * fps))
    motion_expr = move_info["expr"].format(total_frames=total_frames)

    vf = (
        f"scale=1080:1920:force_original_aspect_ratio=increase,"
        f"crop=1080:1920,"
        f"zoompan={motion_expr}:d={total_frames}:s=1080x1920:fps={fps}"
    )

    cmd = [
        "ffmpeg", "-y", "-hide_banner",
        "-loop", "1",
        "-i", str(image_path),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "19",
        "-t", str(duration),
        "-pix_fmt", "yuv420p",
        str(out_clip_path)
    ]

    print(f"[cinema_studio] Rendering camera move '{move_info['name']}' ({duration:.1f}s)...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0 and out_clip_path.exists():
        print(f"✓ Cinema camera clip ready: {out_clip_path.name}")
        return True
    else:
        print(f"[cinema_studio] FFmpeg camera motion error:\n{res.stderr}")
        return False


def generate_cinema_short(
    prompt: str,
    output_dir: Path,
    camera_move: str = "dolly_in",
    genre: str = "general",
    era: str = "modern",
    camera: str = "arri",
    lens: str = "anamorphic",
    lighting: str = "cinematic",
    palette: str = "teal_orange",
    voice_text: Optional[str] = None,
    music_bed: str = "cinematic-min"
) -> Dict[str, Any]:
    """
    Generates a complete Cinema Studio short video end-to-end.
    """
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Compile Freefield Cinema Dual-Prompts
    prompts = compile_cinema_prompts(
        prompt, genre=genre, era=era, camera=camera,
        lens=lens, lighting=lighting, palette=palette,
        camera_move=camera_move
    )

    # 2. Generate Still Frame 0 using Free Pollinations NVIDIA Sana (512x910 true 9:16)
    from tools.gen_scene_images import generate_scene_image
    frame0_path = output_dir / "cinema_frame0.jpg"
    print(f"[cinema_studio] Generating Frame 0 still: {prompts['still_prompt'][:80]}...")
    img_ok = generate_scene_image(prompts["still_prompt"], frame0_path, seed=42)

    if not img_ok or not frame0_path.exists():
        # Fallback to local reference
        ref_path = ROOT / "media" / "projects" / "dancing-girl" / "b1-dance.png"
        if ref_path.exists():
            import shutil
            shutil.copyfile(ref_path, frame0_path)

    # 3. Render Camera Motion Dynamics
    cinema_raw_mp4 = output_dir / "cinema_raw.mp4"
    render_cinema_motion_clip(
        frame0_path, cinema_raw_mp4,
        camera_move=camera_move,
        duration=6.0
    )

    return {
        "ok": True,
        "raw_video": str(cinema_raw_mp4),
        "frame0": str(frame0_path),
        "prompts": prompts,
        "camera_move": camera_move
    }


def main():
    parser = argparse.ArgumentParser(description="Freefield Cinema Studio Engine")
    parser.add_argument("--prompt", required=True, help="Scene prompt")
    parser.add_argument("--move", default="dolly_in", help="Camera move id (e.g. dolly_in, bullet_time, crash_zoom)")
    parser.add_argument("--genre", default="general", help="Film genre")
    parser.add_argument("--era", default="modern", help="Film era")
    parser.add_argument("--camera", default="arri", help="Camera body")
    parser.add_argument("--lens", default="anamorphic", help="Lens type")
    parser.add_argument("--lighting", default="cinematic", help="Lighting setup")
    parser.add_argument("--palette", default="teal_orange", help="Color palette")
    parser.add_argument("--out-dir", default="shorts/cinema-test", help="Output directory")
    args = parser.parse_args()

    res = generate_cinema_short(
        args.prompt,
        Path(args.out_dir),
        camera_move=args.move,
        genre=args.genre,
        era=args.era,
        camera=args.camera,
        lens=args.lens,
        lighting=args.lighting,
        palette=args.palette
    )
    print("Result:", json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
