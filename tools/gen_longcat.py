#!/usr/bin/env python3
"""
gen_longcat.py — Meituan LongCat-Video Generation Client.

LongCat-Video is Meituan's open-source 13.6B foundation video generation model
and audio-driven human talking-avatar system (https://github.com/meituan-longcat/LongCat-Video).

It unifies Text-to-Video (T2V), Image-to-Video (I2V), and Talking Avatar generation.
Because local inference requires 16GB–40GB VRAM (user GPU: 4GB VRAM), this client supports:
  1. Google Colab Tunnel Endpoint (LONGCAT_ENDPOINT or COLAB_VIDEO_ENDPOINT) — Free on Colab!
  2. Hugging Face Spaces API for LongCat-Video
  3. Local runner wrapper if user clones the repo into tools/longcat

Usage:
  python tools/gen_longcat.py --prompt "A cute little girl dancing happily" --out output/longcat.mp4
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent.parent

def load_env():
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

def generate_via_colab_tunnel(prompt, out_path, endpoint_url, aspect_ratio="9:16"):
    """Sends prompt to LongCat-Video running on Google Colab."""
    print(f"Connecting to Meituan LongCat-Video on Colab tunnel: {endpoint_url}...")
    endpoint_url = endpoint_url.rstrip("/")
    api_url = f"{endpoint_url}/api/generate" if not endpoint_url.endswith("/api/generate") else endpoint_url

    payload = {
        "model": "longcat-video",
        "prompt": prompt,
        "aspect_ratio": aspect_ratio
    }

    req = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "VideoAI/1.0"}
    )

    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read().decode())
            video_url = data.get("video_url") or data.get("url")
            if video_url:
                if video_url.startswith("/"):
                    video_url = f"{endpoint_url}{video_url}"
                print(f"Downloading video from LongCat Colab tunnel: {video_url}...")
                out_path.parent.mkdir(parents=True, exist_ok=True)
                urllib.request.urlretrieve(video_url, str(out_path))
                print(f"✓ Video saved to: {out_path}")
                return True
    except Exception as e:
        print(f"[LongCat Colab Error] {e}")
        return False

def generate_via_hf_spaces(prompt, out_path, aspect_ratio="9:16"):
    """Queries Hugging Face Space for Meituan LongCat."""
    print("Checking Hugging Face Spaces for Meituan LongCat-Video...")
    try:
        url = "https://meituan-longcat-longcat-video.hf.space/api/predict"
        payload = {"data": [prompt, 30, 6.0, "9:16"]}
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
            if "data" in data and len(data["data"]) > 0:
                res_url = data["data"][0]
                if isinstance(res_url, dict):
                    res_url = res_url.get("name") or res_url.get("url")
                if res_url:
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    urllib.request.urlretrieve(res_url, str(out_path))
                    print(f"✓ Video saved to: {out_path}")
                    return True
    except Exception as e:
        print(f"[HF Space Error] {e}")
    return False

def main():
    parser = argparse.ArgumentParser(description="Meituan LongCat-Video Client")
    parser.add_argument("--prompt", required=True, help="Video prompt")
    parser.add_argument("--out", default="output/longcat.mp4", help="Output MP4 path")
    parser.add_argument("--provider", choices=["auto", "colab", "hf"], default="auto")
    args = parser.parse_args()

    env = load_env()
    out_path = Path(args.out).resolve()
    colab_endpoint = env.get("LONGCAT_ENDPOINT") or env.get("COLAB_VIDEO_ENDPOINT")

    provider = args.provider
    if provider == "auto":
        if colab_endpoint:
            provider = "colab"
        else:
            print("=" * 60)
            print("Meituan LongCat-Video (13.6B Parameters)")
            print("=" * 60)
            print("Notice: LongCat-Video requires 16GB–40GB VRAM (your GPU has 4GB VRAM).")
            print("To generate with LongCat-Video:")
            print("  Option 1 (100% Free): Launch the Google Colab Notebook in `colab/VideoAI_Unified_Studio.ipynb`")
            print("           and set COLAB_VIDEO_ENDPOINT=<your-tunnel-url> in .env")
            print("  Option 2: Use huggingface.co/spaces/meituan-longcat/LongCat-Video")
            print("=" * 60)
            sys.exit(1)

    success = False
    if provider == "colab" and colab_endpoint:
        success = generate_via_colab_tunnel(args.prompt, out_path, colab_endpoint)
    elif provider == "hf":
        success = generate_via_hf_spaces(args.prompt, out_path)

    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
