#!/usr/bin/env python3
"""
gen_hunyuan.py — Tencent HunyuanVideo Generation Client.

HunyuanVideo is a 13B-parameter open-source text-to-video foundation model
by Tencent (https://github.com/Tencent-Hunyuan/HunyuanVideo).

Because running HunyuanVideo locally requires 14GB–60GB VRAM (user GPU: 4GB VRAM),
this client supports:
  1. Google Colab Tunnel Endpoint (HUNYUAN_ENDPOINT or COLAB_VIDEO_ENDPOINT) — 100% Free on Colab T4/A100!
  2. Serverless Cloud via Replicate (REPLICATE_API_TOKEN)
  3. Serverless Cloud via Fal.ai (FAL_KEY)
  4. Local ComfyUI / Gradio instance (if running on a remote rig)

Usage:
  python tools/gen_hunyuan.py --prompt "A cute little girl dancing happily" --out output/hunyuan.mp4
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.parse
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
    """Sends prompt to a running Google Colab / Gradio tunnel instance."""
    print(f"Connecting to Google Colab / Gradio endpoint at: {endpoint_url}...")
    endpoint_url = endpoint_url.rstrip("/")
    api_url = f"{endpoint_url}/api/generate" if not endpoint_url.endswith("/api/generate") else endpoint_url
    
    payload = {
        "model": "hunyuan-video",
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "steps": 30
    }
    
    req = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "VideoAI/1.0"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            video_url = data.get("video_url") or data.get("url")
            if video_url:
                if video_url.startswith("/"):
                    video_url = f"{endpoint_url}{video_url}"
                print(f"Downloading video from Colab tunnel: {video_url}...")
                out_path.parent.mkdir(parents=True, exist_ok=True)
                urllib.request.urlretrieve(video_url, str(out_path))
                print(f"✓ Video saved to: {out_path}")
                return True
    except Exception as e:
        print(f"[Colab Tunnel Error] {e}")
        return False

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
    parser.add_argument("--provider", choices=["auto", "colab", "replicate", "fal"], default="auto")
    parser.add_argument("--aspect", default="9:16", help="Aspect ratio (e.g. 9:16, 16:9)")
    args = parser.parse_args()

    env = load_env()
    out_path = Path(args.out).resolve()
    colab_endpoint = env.get("HUNYUAN_ENDPOINT") or env.get("COLAB_VIDEO_ENDPOINT")
    replicate_token = env.get("REPLICATE_API_TOKEN")
    fal_key = env.get("FAL_KEY")

    provider = args.provider
    if provider == "auto":
        if colab_endpoint:
            provider = "colab"
        elif fal_key:
            provider = "fal"
        elif replicate_token:
            provider = "replicate"
        else:
            print("=" * 60)
            print("Tencent HunyuanVideo (13B Parameters)")
            print("=" * 60)
            print("Notice: Running HunyuanVideo requires 14GB–45GB VRAM (your GPU has 4GB VRAM).")
            print("To generate with HunyuanVideo:")
            print("  Option 1 (100% Free): Launch the Google Colab Notebook in `colab/VideoAI_Unified_Studio.ipynb`")
            print("           and set COLAB_VIDEO_ENDPOINT=<your-tunnel-url> in .env")
            print("  Option 2: Add FAL_KEY in .env (fal.ai/dashboard/keys)")
            print("  Option 3: Add REPLICATE_API_TOKEN in .env (replicate.com/account/api-tokens)")
            print("=" * 60)
            sys.exit(1)

    success = False
    if provider == "colab" and colab_endpoint:
        success = generate_via_colab_tunnel(args.prompt, out_path, colab_endpoint, args.aspect)
    elif provider == "fal" and fal_key:
        success = generate_via_fal(args.prompt, out_path, fal_key, args.aspect)
    elif provider == "replicate" and replicate_token:
        success = generate_via_replicate(args.prompt, out_path, replicate_token, args.aspect)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
