#!/usr/bin/env python3
"""
character_consistency.py — Character Consistency & Identity Engine.

Provides persistent character identity sheets across multi-scene video shorts:
- Locks facial features, hairstyle, signature outfit, color palette, and visual style.
- Injects character anchors into every scene prompt so the protagonist looks
  consistent across scene 1, 2, 3, etc.
- Offers curated presets (3D Cartoon, Cinematic, Anime, Cyberpunk, Documentary)
  and custom user persona definitions.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional

ROOT = Path(__file__).resolve().parent.parent

BUILTIN_PERSONAS = {
    "3d_cartoon": {
        "id": "3d_cartoon",
        "name": "3D Cartoon / Pixar Hero",
        "style_name": "3D Pixar Animation",
        "character_name": "Sammy",
        "prompt_prefix": (
            "Pixar 3D animated character design, adorable cute protagonist with expressive hazel eyes, "
            "styled chestnut hair, wearing a stylish blue hoodie with orange lining and sneakers, "
            "soft subsurface scattering, Disney Pixar aesthetic, high fidelity 3D render, octane render"
        ),
        "negative_prompt": (
            "photorealistic, real life photo, deformed face, bad anatomy, ugly, duplicate limbs, "
            "mutated hands, missing fingers, extra limbs, distorted eyes, blurry, flat 2d"
        ),
        "base_seed": 1042
    },
    "cinematic": {
        "id": "cinematic",
        "name": "Cinematic Photorealistic Hero",
        "style_name": "Cinematic 8K",
        "character_name": "Maya",
        "prompt_prefix": (
            "Cinematic 8K photorealistic portrait, sharp focus, charismatic explorer with warm hazel eyes, "
            "dark braided hair, wearing a rugged dark olive outdoor jacket with tactical collar, "
            "dramatic volumetric rim lighting, natural skin texture, movie still from a blockbuster film"
        ),
        "negative_prompt": (
            "cartoon, illustration, painting, drawing, CGI, distorted face, bad anatomy, deformed eyes, "
            "extra fingers, duplicate body, blurry, low resolution, overexposed"
        ),
        "base_seed": 2048
    },
    "anime": {
        "id": "anime",
        "name": "Modern Anime / Shinkai Protagonist",
        "style_name": "Makoto Shinkai Anime",
        "character_name": "Ren",
        "prompt_prefix": (
            "Makoto Shinkai modern anime aesthetic, beautiful cel-shaded character, determined expressive eyes, "
            "sleek navy blue hair, wearing a minimalist modern windbreaker over a white t-shirt, "
            "vibrant anime sky lighting, high detail anime masterpiece, trending on Pixiv"
        ),
        "negative_prompt": (
            "3d render, live action, western cartoon, disfigured face, bad anatomy, extra arms, "
            "blurry, poorly drawn hands, lowres"
        ),
        "base_seed": 3096
    },
    "cyberpunk": {
        "id": "cyberpunk",
        "name": "Cyberpunk Neon Runner",
        "style_name": "Cyberpunk Futuristic",
        "character_name": "Kael",
        "prompt_prefix": (
            "Cyberpunk futuristic character, subtle glowing cyan neural cyberware on cheekbone, "
            "sharp athletic build, undercut haircut, wearing an illuminated high-collar techwear jacket "
            "with reflective circuitry patterns, rainy neon reflections, Blade Runner aesthetic"
        ),
        "negative_prompt": (
            "medieval, fantasy, lowres, bad hands, mutated fingers, distorted face, cartoon, blurry, flat"
        ),
        "base_seed": 4096
    },
    "documentary": {
        "id": "documentary",
        "name": "Historical / Archival Figure",
        "style_name": "Archival Documentary",
        "character_name": "Professor Vance",
        "prompt_prefix": (
            "Historical documentary figure, scholarly intellectual with round wire-rimmed glasses, "
            "neat graying hair, wearing a tweed blazer with elbow patches and a vintage pocket watch, "
            "warm archival studio lighting, National Geographic style documentary portrait"
        ),
        "negative_prompt": (
            "cartoon, 3d render, anime, sci-fi, blurry, deformed face, bad eyes, duplicate limbs"
        ),
        "base_seed": 5120
    }
}

class CharacterConsistencyEngine:
    def __init__(self, persona_id: str = "3d_cartoon", custom_persona: Optional[Dict[str, Any]] = None):
        if custom_persona:
            self.persona = {
                "id": custom_persona.get("id", "custom"),
                "name": custom_persona.get("name", "Custom Character"),
                "style_name": custom_persona.get("style_name", "Custom Style"),
                "character_name": custom_persona.get("character_name", "Protagonist"),
                "prompt_prefix": custom_persona.get("prompt_prefix", ""),
                "negative_prompt": custom_persona.get("negative_prompt", "deformed face, bad anatomy, blurry"),
                "base_seed": int(custom_persona.get("base_seed", 1234))
            }
        else:
            self.persona = BUILTIN_PERSONAS.get(persona_id, BUILTIN_PERSONAS["3d_cartoon"]).copy()

    def get_scene_prompt(self, scene_action: str, scene_index: int = 0) -> str:
        """
        Synthesizes a full visual prompt for a specific scene by seamlessly injecting
        the locked character appearance and style tokens into the scene action/setting.
        """
        prefix = self.persona["prompt_prefix"]
        char_name = self.persona["character_name"]
        
        # Combine character identity with scene environment and action
        full_prompt = (
            f"{prefix}, featuring {char_name} {scene_action.strip()}. "
            f"Consistent facial appearance, identical outfit and colors, vertical 9:16 composition, "
            f"cinematic high detail masterpiece"
        )
        return full_prompt

    def get_scene_seed(self, scene_index: int = 0) -> int:
        """
        Returns a deterministic seed for the scene that preserves visual consistency
        while providing natural shot variation.
        """
        return self.persona["base_seed"] + (scene_index * 19)

    def get_negative_prompt(self) -> str:
        return self.persona.get("negative_prompt", "")

def get_available_personas():
    return [
        {
            "id": p["id"],
            "name": p["name"],
            "style": p["style_name"],
            "char": p["character_name"]
        }
        for p in BUILTIN_PERSONAS.values()
    ]

if __name__ == "__main__":
    engine = CharacterConsistencyEngine("3d_cartoon")
    prompt = engine.get_scene_prompt("dancing excitedly in a colorful room filled with confetti", scene_index=0)
    print("Character Consistency Test:")
    print("Persona:", engine.persona["name"])
    print("Seed:", engine.get_scene_seed(0))
    print("Scene Prompt:\n", prompt)
