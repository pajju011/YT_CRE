#!/usr/bin/env python3
"""
gen_freevideo.py — FlashML FreeVideo (MiniMax H3) Generation Client.

FreeVideo is an open-source inference engine designed by FlashML to run
the MiniMax H3 video generation model on consumer hardware (8GB+ VRAM)
or via cloud/Colab (https://github.com/FlashML-org/FreeVideo).

Because user GPU has 4GB VRAM (MiniMax H3 requires 8GB+ VRAM & 16GB RAM minimum),
this client supports:
  1. Google Colab Tunnel Endpoint (FREEVIDEO_ENDPOINT or COLAB_VIDEO_ENDPOINT)
  2. Local FreeVideo CLI (if installed locally with CPU/RAM offloading)
  3. MiniMax Cloud API / Fal.ai (MINIMAX_API_KEY or FAL_KEY)

Usage:
  python tools/gen_freevideo.py --prompt "A cute little girl dancing happily" --out output/freevideo.mp4
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
    """Sends request to FreeVideo running inside Google Colab."""
    print(f"Connecting to FreeVideo on Google Colab / Tunnel: {endpoint_url}...")
    endpoint_url = endpoint_url.rstrip("/")
    api_url = f"{endpoint_url}/api/generate" if not endpoint_url.endswith("/api/generate") else endpoint_url

    payload = {
        "model": "freevideo",
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
                print(f"Downloading video from FreeVideo Colab tunnel: {video_url}...")
                out_path.parent.mkdir(parents=True, exist_ok=True)
                urllib.request.urlretrieve(video_url, str(out_path))
                print(f"✓ Video saved to: {out_path}")
                return True
    except Exception as e:
        print(f"[FreeVideo Colab Error] {e}")
        return False

def generate_via_local_freevideo(prompt, out_path, local_bin):
    """Executes local FreeVideo CLI if present."""
    print(f"Executing local FreeVideo: {local_bin}...")
    cmd = [
        str(local_bin),
        "--prompt", prompt,
        "--output", str(out_path),
        "--offload", "true"
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and out_path.exists():
            print(f"✓ FreeVideo generated local video: {out_path}")
            return True
        else:
            print(f"FreeVideo execution failed: {res.stderr}")
            return False
    except Exception as e:
        print(f"Error launching FreeVideo: {e}")
        return False

def generate_via_fal_minimax(prompt, out_path, key):
    """Runs MiniMax Video on Fal.ai."""
    print("Connecting to MiniMax Video on Fal.ai...")
    url = "https://queue.fal.run/fal-ai/minimax-video"
    headers = {
        "Authorization": f"Key {key}",
        "Content-Type": "application/json",
        "User-Agent": "VideoGenerator/1.0"
    }

    payload = {
        "prompt": prompt,
        "aspect_ratio": "9:16"
    }

    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Fal MiniMax Error {e.code}: {e.read().decode()}")
        return False

    request_id = data.get("request_id")
    poll_url = f"https://queue.fal.run/fal-ai/minimax-video/requests/{request_id}/status"
    print(f"Queued on Fal MiniMax (ID: {request_id}). Waiting for video...")

    while True:
        time.sleep(3)
        poll_req = urllib.request.Request(poll_url, headers=headers)
        with urllib.request.urlopen(poll_req) as resp:
            status_data = json.loads(resp.read().decode())
            status = status_data.get("status")
            print(f"  Status: {status}...")

            if status == "COMPLETED":
                res_url = f"https://queue.fal.run/fal-ai/minimax-video/requests/{request_id}"
                with urllib.request.urlopen(urllib.request.Request(res_url, headers=headers)) as r_resp:
                    res_data = json.loads(r_resp.read().decode())
                    video_url = res_data.get("video", {}).get("url")
                    if video_url:
                        out_path.parent.mkdir(parents=True, exist_ok=True)
                        urllib.request.urlretrieve(video_url, str(out_path))
                        print(f"✓ Video saved to: {out_path}")
                        return True
            elif status in ("FAILED", "ERROR"):
                print("Generation failed on Fal MiniMax")
                return False

def main():
    parser = argparse.ArgumentParser(description="FlashML FreeVideo Client")
    parser.add_argument("--prompt", required=True, help="Video prompt")
    parser.add_argument("--out", default="output/freevideo.mp4", help="Output MP4 path")
    parser.add_argument("--provider", choices=["auto", "colab", "local", "fal"], default="auto")
    args = parser.parse_args()

    env = load_env()
    out_path = Path(args.out).resolve()
    colab_endpoint = env.get("FREEVIDEO_ENDPOINT") or env.get("COLAB_VIDEO_ENDPOINT")
    fal_key = env.get("FAL_KEY")
    local_bin = None
    for candidate in [ROOT / "tools" / "freevideo" / "FreeVideo.exe", Path("C:/FreeVideo/FreeVideo.exe")]:
        if candidate.exists():
            local_bin = candidate
            break

    provider = args.provider
    if provider == "auto":
        if colab_endpoint:
            provider = "colab"
        elif local_bin:
            provider = "local"
        elif fal_key:
            provider = "fal"
        else:
            print("=" * 60)
            print("FlashML FreeVideo (MiniMax H3 Engine)")
            print("=" * 60)
            print("Notice: FreeVideo requires at least 8GB VRAM (your GPU has 4GB VRAM).")
            print("To generate with FreeVideo:")
            print("  Option 1 (100% Free): Launch the Google Colab Notebook in `colab/VideoAI_Unified_Studio.ipynb`")
            print("           and set COLAB_VIDEO_ENDPOINT=<your-tunnel-url> in .env")
            print("  Option 2: Add FAL_KEY in .env (fal.ai/dashboard/keys)")
            print("  Option 3: Download FreeVideo from github.com/FlashML-org/FreeVideo into tools/freevideo")
            print("=" * 60)
            sys.exit(1)

    success = False
    if provider == "colab" and colab_endpoint:
        success = generate_via_colab_tunnel(args.prompt, out_path, colab_endpoint)
    elif provider == "local" and local_bin:
        success = generate_via_local_freevideo(args.prompt, out_path, local_bin)
    elif provider == "fal" and fal_key:
        success = generate_via_fal_minimax(args.prompt, out_path, fal_key)

    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
