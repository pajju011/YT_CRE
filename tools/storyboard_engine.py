#!/usr/bin/env python3
"""
storyboard_engine.py — Complete Multi-Scene Storyboard & Consistency Engine.

Orchestrates:
1. Story Decomposition: breaks prompt into 4-6 narrative beats (Hook, Setup, Build, Reveal, Loop).
2. Character Consistency: locks character traits across all scenes.
3. Scene Imagery: generates 9:16 vertical scene stills.
4. Camera Dynamics: animates each scene with camera motion.
5. Sequencing: stitches clips and generates synchronized beats.json for voice & captions.
"""
import argparse
import json
import os
from pathlib import Path
import re
import sys
from typing import List, Dict, Any, Optional

ROOT = Path(__file__).resolve().parent.parent

try:
    from tools.character_consistency import CharacterConsistencyEngine, BUILTIN_PERSONAS
    from tools.gen_scene_images import generate_scene_image
    from tools.animate_scenes import animate_scene_still, stitch_scene_clips, MOTION_PRESETS
except ImportError:
    # Adjust import path if running directly
    sys.path.append(str(ROOT))
    from tools.character_consistency import CharacterConsistencyEngine, BUILTIN_PERSONAS
    from tools.gen_scene_images import generate_scene_image
    from tools.animate_scenes import animate_scene_still, stitch_scene_clips, MOTION_PRESETS

DEFAULT_MOTIONS = ["zoom_in", "pan_right", "tilt_up", "zoom_out", "pan_left", "breathing"]

def decompose_story(topic: str, persona_name: str, scene_count: int = 4) -> List[Dict[str, Any]]:
    """
    Decomposes a video topic/prompt into structured narrative scenes.
    """
    topic_clean = topic.strip()
    
    # Template beat archetypes
    beat_archetypes = [
        {
            "beat": "hook",
            "title": "The Hook",
            "action": f"looking directly forward with intense curiosity and astonishment at a mysterious glowing phenomenon",
            "narration": f"Have you ever wondered what happens when {topic_clean} unfolds before your eyes?",
            "motion": "zoom_in",
            "duration": 4.0
        },
        {
            "beat": "setup",
            "title": "The Discovery",
            "action": f"walking cautiously through the vast environment, examining unexpected clues and intricate details",
            "narration": f"It all begins with a hidden pattern that most people completely overlook.",
            "motion": "pan_right",
            "duration": 4.5
        },
        {
            "beat": "build",
            "title": "The Action",
            "action": f"actively demonstrating the technique with bright energetic sparks flying and focused determination",
            "narration": f"Every single step moves faster and faster, building unstoppable momentum.",
            "motion": "tilt_up",
            "duration": 4.5
        },
        {
            "beat": "reveal",
            "title": "The Hero Moment",
            "action": f"celebrating the breakthrough achievement with a triumphant smile as brilliant radiant lights illuminate the scene",
            "narration": f"And suddenly, the entire puzzle clicks into place with breathtaking clarity!",
            "motion": "zoom_out",
            "duration": 4.5
        },
        {
            "beat": "loop",
            "title": "The Twist & Loop",
            "action": f"smiling warmly, pointing back toward the beginning with an inviting and confident gesture",
            "narration": f"Now watch closely, and let's experience the entire journey once again.",
            "motion": "breathing",
            "duration": 4.0
        }
    ]

    selected_beats = beat_archetypes[:scene_count]
    return selected_beats

def build_storyboard(
    topic: str,
    project_dir: Path,
    persona_id: str = "3d_cartoon",
    custom_persona: Optional[Dict[str, Any]] = None,
    scene_count: int = 4,
    custom_scenes: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Generates a complete multi-scene storyboard short with character consistency.
    """
    project_dir = Path(project_dir).resolve()
    scenes_dir = project_dir / "scenes"
    output_dir = project_dir / "output"
    scenes_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    char_engine = CharacterConsistencyEngine(persona_id, custom_persona)
    beats = custom_scenes if custom_scenes else decompose_story(topic, char_engine.persona["name"], scene_count)

    rendered_scenes = []
    clip_paths = []
    vo_items = []
    current_time = 0.0

    print(f"🎬 Starting Storyboard Generation: {len(beats)} scenes for persona '{char_engine.persona['name']}'...")

    for idx, beat in enumerate(beats, 1):
        scene_id = f"scene_{idx:02d}"
        img_path = scenes_dir / f"{scene_id}.png"
        clip_path = scenes_dir / f"{scene_id}.mp4"
        motion = beat.get("motion", DEFAULT_MOTIONS[idx % len(DEFAULT_MOTIONS)])
        duration = float(beat.get("duration", 4.0))

        # 1. Synthesize visual prompt with character consistency
        action = beat.get("action", beat.get("prompt", topic))
        visual_prompt = char_engine.get_scene_prompt(action, scene_index=idx)
        seed = char_engine.get_scene_seed(scene_index=idx)

        # 2. Generate Scene Still Image
        print(f"\n[Scene {idx}/{len(beats)}] Generating still...")
        img_ok = generate_scene_image(visual_prompt, img_path, seed=seed, width=512, height=910)

        # 3. Animate Scene into 1080x1920 MP4 clip
        print(f"[Scene {idx}/{len(beats)}] Animating camera [{motion}]...")
        clip_ok = animate_scene_still(img_path, clip_path, motion=motion, duration=duration)

        if clip_ok:
            clip_paths.append(clip_path)

        narration = beat.get("narration", beat.get("text", ""))
        vo_items.append({
            "beat": beat.get("beat", f"scene_{idx}"),
            "text": narration,
            "start": round(current_time, 2),
            "end": round(current_time + duration, 2)
        })
        current_time += duration

        rendered_scenes.append({
            "id": scene_id,
            "title": beat.get("title", f"Scene {idx}"),
            "visual_prompt": visual_prompt,
            "narration": narration,
            "motion": motion,
            "duration": duration,
            "image_url": "/" + str(img_path.relative_to(ROOT)).replace("\\", "/") if img_path.exists() else None,
            "clip_url": "/" + str(clip_path.relative_to(ROOT)).replace("\\", "/") if clip_path.exists() else None
        })

    # 4. Stitch All Scene Clips
    stitched_video = output_dir / "storyboard_raw.mp4"
    print(f"\n🎬 Stitching {len(clip_paths)} scene clips into {stitched_video.name}...")
    stitch_ok = stitch_scene_clips(clip_paths, stitched_video)

    # 5. Save beats.json
    beats_file = project_dir / "beats.json"
    beats_data = {
        "title": topic.title(),
        "persona": char_engine.persona["name"],
        "duration": round(current_time, 2),
        "scenes": rendered_scenes,
        "vo": vo_items
    }
    with open(beats_file, "w", encoding="utf-8") as f:
        json.dump(beats_data, f, indent=2, ensure_ascii=False)

    print(f"✓ Storyboard compiled successfully!")
    print(f"  Raw Video: {stitched_video}")
    print(f"  Beats File: {beats_file}")

    return {
        "ok": stitch_ok,
        "raw_video": str(stitched_video),
        "beats_file": str(beats_file),
        "scenes": rendered_scenes,
        "total_duration": current_time
    }

def main():
    parser = argparse.ArgumentParser(description="Multi-Scene Storyboard Generator")
    parser.add_argument("--prompt", required=True, help="Video topic / prompt")
    parser.add_argument("--project", default="shorts/storyboard-test", help="Project folder")
    parser.add_argument("--persona", default="3d_cartoon", choices=list(BUILTIN_PERSONAS.keys()), help="Character persona")
    parser.add_argument("--scenes", type=int, default=4, help="Number of scenes")
    args = parser.parse_args()

    p_dir = ROOT / args.project
    build_storyboard(args.prompt, p_dir, persona_id=args.persona, scene_count=args.scenes)

if __name__ == "__main__":
    main()
