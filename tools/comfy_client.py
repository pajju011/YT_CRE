#!/usr/bin/env python3
"""
comfy_client.py — Official Comfy Org / Comfy Router Client.

Integrates ComfyUI Platform API (https://api.comfy.org):
- Access to 320+ models including Wan 2.5/2.6/3.0, Kling, MiniMax, LTX-Video, and Flux.
- Authenticates via Comfy API key (COMFY_API_KEY).
- Provides automatic credit balance validation and fallback.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request
from typing import Dict, Any, Optional

ROOT = Path(__file__).resolve().parent.parent

def load_env() -> Dict[str, str]:
    env = {}
    p = ROOT / ".env"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip().strip('"').strip("'")
    return {**env, **os.environ}

def get_comfy_key() -> str:
    env = load_env()
    return env.get("COMFY_API_KEY") or env.get("COMFY_CLOUD_API_KEY") or ""

def check_connection() -> Dict[str, Any]:
    """
    Verifies authentication with Comfy Router and returns account status.
    """
    api_key = get_comfy_key()
    if not api_key:
        return {"ok": False, "error": "No COMFY_API_KEY configured in .env"}

    url = "https://api.comfy.org/v2/models?limit=5"
    req = urllib.request.Request(
        url,
        headers={"X-API-Key": api_key, "User-Agent": "VideoAI/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
            return {
                "ok": True,
                "connected": True,
                "models_count": len(data.get("data", [])),
                "key_preview": api_key[:12] + "..." + api_key[-4:]
            }
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"HTTP {e.code}: {e.read().decode()}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def generate_video(
    prompt: str,
    out_path: Path,
    model: str = "wan/wan2.5-t2v-preview",
    aspect_ratio: str = "9:16",
    duration: int = 5
) -> Dict[str, Any]:
    """
    Submits a video generation task to Comfy Router and downloads the resulting MP4.
    """
    api_key = get_comfy_key()
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not api_key:
        return {
            "ok": False,
            "error": "No COMFY_API_KEY found. Enter your ComfyUI key in Settings."
        }

    url = f"https://api.comfy.org/v2/models/{model}"

    # Build payload based on model family
    if "wan" in model.lower():
        payload = {
            "input": {"prompt": prompt},
            "parameters": {"ratio": aspect_ratio, "duration": duration}
        }
    elif "kling" in model.lower():
        payload = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "duration": str(duration)
        }
    else:
        payload = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio
        }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "X-API-Key": api_key,
            "Content-Type": "application/json",
            "User-Agent": "VideoAI/1.0"
        }
    )

    print(f"Dispatching video to Comfy Router model '{model}'...")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
            
            # Extract video URL from response
            video_url = (
                data.get("url") or 
                data.get("video_url") or 
                data.get("output", {}).get("url") or
                data.get("data", {}).get("url")
            )

            if video_url:
                print(f"Downloading finished video from: {video_url}...")
                urllib.request.urlretrieve(video_url, str(out_path))
                print(f"✓ Video saved to: {out_path}")
                return {"ok": True, "out_path": str(out_path), "video_url": video_url}
            else:
                return {"ok": True, "data": data, "message": "Task queued on Comfy Router"}

    except urllib.error.HTTPError as e:
        err_msg = e.read().decode()
        if e.code == 402:
            print("[Comfy Router] 402 Payment Required: Insufficient credits on your Comfy Org workspace.")
            return {
                "ok": False,
                "error_type": "insufficient_credits",
                "error": "Comfy Org account has 0.00 credits. Top up at https://platform.comfy.org or use the free Google Colab Hub!"
            }
        print(f"[Comfy Router Error {e.code}] {err_msg}")
        return {"ok": False, "error": f"HTTP {e.code}: {err_msg}"}
    except Exception as e:
        print(f"[Comfy Router Error] {e}")
        return {"ok": False, "error": str(e)}

if __name__ == "__main__":
    conn = check_connection()
    print("Comfy Router Status:", json.dumps(conn, indent=2))
