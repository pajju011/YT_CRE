#!/usr/bin/env python3
"""
gen_hunyuan.py — Tencent HunyuanVideo generation client.

HunyuanVideo is a 13B-parameter open-source text-to-video foundation model.
Because running it locally requires 45GB-60GB VRAM (or 16GB+ VRAM with heavy quantization),
this tool runs HunyuanVideo via serverless cloud endpoints (Replicate or Fal.ai)
using pure Python standard library (no extra pip installs needed).

Usage:
  python tools/gen_hunyuan.py --prompt "A cute little girl dancing happily, cartoon 3D" --out output/dance.mp4
  python tools/gen_hunyuan.py --provider replicate --prompt "..." --out clip.mp4
  python tools/gen_hunyuan.py --provider fal --prompt "..." --out clip.mp4

Requirements:
  - For Replicate: REPLICATE_API_TOKEN in .env (get one at replicate.com/account/api-tokens)
  - For Fal.ai:    FAL_KEY in .env (get one at fal.ai/dashboard/keys)
"""
import argparse
import json
import os
from pathlib import Path
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

def generate_via_replicate(prompt, out_path, token, aspect_ratio="9:16"):
    """Runs Tencent HunyuanVideo on Replicate serverless A100 GPUs."""
    print("Connecting to Tencent HunyuanVideo on Replicate...")
    url = "https://api.replicate.com/v1/models/tencent/hunyuan-video/predictions"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "VideoGenerator/1.0"
    }

    payload = {
        "input": {
            "prompt": prompt,
            "resolution": "720p",
            "flow_shift": 7,
            "infer_steps": 30,
            "guidance_scale": 6
        }
    }

    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            prediction = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Replicate API Error {e.code}: {e.read().decode()}")
        return False

    pred_id = prediction["id"]
    poll_url = prediction["urls"]["get"]
    print(f"Prediction started (ID: {pred_id}). Waiting for video generation...")

    while True:
        time.sleep(3)
        poll_req = urllib.request.Request(poll_url, headers=headers)
        with urllib.request.urlopen(poll_req) as resp:
            status_data = json.loads(resp.read().decode())
            status = status_data["status"]
            print(f"  Status: {status}...")

            if status == "succeeded":
                output_url = status_data["output"]
                print(f"Downloading video from {output_url}...")
                out_path.parent.mkdir(parents=True, exist_ok=True)
                urllib.request.urlretrieve(output_url, str(out_path))
                print(f"✓ Video saved to: {out_path}")
                return True
            elif status in ("failed", "canceled"):
                print(f"Generation failed: {status_data.get('error')}")
                return False

def generate_via_fal(prompt, out_path, key, aspect_ratio="9:16"):
    """Runs HunyuanVideo on Fal.ai."""
    print("Connecting to Tencent HunyuanVideo on Fal.ai...")
    url = "https://queue.fal.run/fal-ai/hunyuan-video"
    headers = {
        "Authorization": f"Key {key}",
        "Content-Type": "application/json",
        "User-Agent": "VideoGenerator/1.0"
    }

    payload = {
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "num_inference_steps": 30
    }

    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Fal API Error {e.code}: {e.read().decode()}")
        return False

    request_id = data.get("request_id")
    poll_url = f"https://queue.fal.run/fal-ai/hunyuan-video/requests/{request_id}/status"
    print(f"Queued on Fal.ai (ID: {request_id}). Waiting for video...")

    while True:
        time.sleep(3)
        poll_req = urllib.request.Request(poll_url, headers=headers)
        with urllib.request.urlopen(poll_req) as resp:
            status_data = json.loads(resp.read().decode())
            status = status_data.get("status")
            print(f"  Status: {status}...")

            if status == "COMPLETED":
                # Fetch result
                res_url = f"https://queue.fal.run/fal-ai/hunyuan-video/requests/{request_id}"
                with urllib.request.urlopen(urllib.request.Request(res_url, headers=headers)) as r_resp:
                    res_data = json.loads(r_resp.read().decode())
                    video_url = res_data.get("video", {}).get("url")
                    if video_url:
                        out_path.parent.mkdir(parents=True, exist_ok=True)
                        urllib.request.urlretrieve(video_url, str(out_path))
                        print(f"✓ Video saved to: {out_path}")
                        return True
            elif status in ("FAILED", "ERROR"):
                print("Generation failed on Fal.ai")
                return False

def main():
    parser = argparse.ArgumentParser(description="Tencent HunyuanVideo Client")
    parser.add_argument("--prompt", required=True, help="Video generation prompt")
    parser.add_argument("--out", default="output/hunyuan_video.mp4", help="Output MP4 file path")
    parser.add_argument("--provider", choices=["auto", "replicate", "fal"], default="auto", help="Cloud API provider")
    parser.add_argument("--aspect", default="9:16", help="Aspect ratio (e.g. 9:16, 16:9)")
    args = parser.parse_args()

    env = load_env()
    replicate_token = env.get("REPLICATE_API_TOKEN", "")
    fal_key = env.get("FAL_KEY", "")

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path

    if args.provider == "replicate" or (args.provider == "auto" and replicate_token):
        if not replicate_token:
            print("Error: REPLICATE_API_TOKEN is not set in .env")
            sys.exit(1)
        ok = generate_via_replicate(args.prompt, out_path, replicate_token, args.aspect)
    elif args.provider == "fal" or (args.provider == "auto" and fal_key):
        if not fal_key:
            print("Error: FAL_KEY is not set in .env")
            sys.exit(1)
        ok = generate_via_fal(args.prompt, out_path, fal_key, args.aspect)
    else:
        print("=" * 60)
        print("Tencent HunyuanVideo Hardware & Setup Notice:")
        print("=" * 60)
        print("HunyuanVideo is a 13B parameter model requiring 45GB-60GB VRAM")
        print("to run locally (your GPU has 4GB VRAM).")
        print("")
        print("To run HunyuanVideo via serverless cloud GPUs, add one of these keys to .env:")
        print("  REPLICATE_API_TOKEN=r8_...   (replicate.com)")
        print("  or")
        print("  FAL_KEY=...                  (fal.ai)")
        print("=" * 60)
        sys.exit(1)

    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
