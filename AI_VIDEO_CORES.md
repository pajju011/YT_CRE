# 🎬 AI Video Generation Cores & Setup Guide

This document explains how the three open-source video generation models requested are integrated into **VideoGenerator AI Studio**:
1. [Tencent HunyuanVideo (13B)](https://github.com/Tencent-Hunyuan/HunyuanVideo)
2. [FlashML FreeVideo (MiniMax H3)](https://github.com/FlashML-org/FreeVideo)
3. [Meituan LongCat-Video (13.6B)](https://github.com/meituan-longcat/LongCat-Video)

---

## ⚡ The Hardware Architecture

| Component | Your Machine | Model Requirements | Solution Provided |
| :--- | :--- | :--- | :--- |
| **GPU** | NVIDIA RTX 2050 (**4 GB VRAM**) | 14 GB – 45 GB VRAM | **Google Colab Free GPU Hub** or **Cloud API** |
| **RAM** | Standard System RAM | 32 GB – 64 GB offload RAM | Unified API Tunnel + Local Compositor |
| **TTS Voice** | Local ONNX Neural Engine | Minimal (<1 GB) | **Kokoro ONNX (100% Local & Free)** |
| **Captions & FX** | Remotion + FFmpeg 8.1 | Minimal (<1 GB) | **Local 1080×1920 Compositor (100% Local)** |

> [!NOTE]
> Running 13B+ diffusion models (HunyuanVideo, LongCat-Video, MiniMax H3) directly on a 4 GB laptop GPU will trigger CUDA Out-Of-Memory (OOM) crashes. Our architecture provides **3 seamless ways** to create full videos without spending a dime or crashing your GPU.

---

## 🛠️ How to Generate Videos (Choose Your Method)

### Method 1: 100% Free Google Colab GPU Hub (Recommended)
We provide a turnkey notebook that runs HunyuanVideo, FreeVideo, and LongCat-Video on **Free Google Colab T4 / A100 GPUs (15 GB – 40 GB VRAM)**:

1. Open [colab/VideoAI_Unified_Studio.ipynb](file:///d:/Antigravity_Projects/VideoGenerator/colab/VideoAI_Unified_Studio.ipynb) in Google Colab:
   - Go to [colab.research.google.com](https://colab.research.google.com)
   - Click **Upload** and select `colab/VideoAI_Unified_Studio.ipynb`
   - Select **Runtime → Change runtime type → T4 GPU**
2. Click **Run All** (or run cells 1, 2, and 3).
3. Copy the public tunnel link printed at the bottom:
   ```
   https://xxxx.trycloudflare.com
   ```
4. In VideoAI Studio (http://localhost:5000), click **⚙️ AI Cores & Endpoints** in the top navigation and paste your tunnel URL into the **Google Colab Tunnel URL** field.
5. Click **Save & Connect**.
6. Select **Tencent HunyuanVideo**, **FlashML FreeVideo**, or **Meituan LongCat-Video** in the dropdown, enter your prompt, and click **Generate Video Short**!

---

### Method 2: Drag & Drop Any Video Clip + Local AI Voiceover & Captions
If you generate clips using free web tools (like Hailuo MiniMax, Kling AI free tier, Luma Dream Machine, or Hugging Face Hunyuan demo):

1. Open **VideoAI Studio** (`run.bat`).
2. Click the **📥 Drag & Drop Existing Video** tab.
3. Drop your `.mp4` video clip into the dropzone.
4. Enter the topic or spoken narration in the prompt box.
5. Choose your voice (Heart, Adam, Bella, Michael) and pacing.
6. Click **Generate Video Short**.
7. In under 5 seconds, the engine:
   - Formats and crops the video to vertical **1080×1920 (9:16)**
   - Synthesizes local **Kokoro AI Voice Narration**
   - Burns **kinetic yellow/white animated subtitles** (TikTok/Shorts style)
   - Mixes sound effects and outputs the final ready-to-post Short!
8. Click **Publish Directly to YouTube Shorts** or **Download Finished Video**.

---

### Method 3: Serverless Cloud APIs (Instant & Zero Setup)
If you prefer fast serverless cloud execution without keeping Google Colab open:
- **Tencent HunyuanVideo**:
  - Add `FAL_KEY` or `REPLICATE_API_TOKEN` in `⚙️ AI Cores & Endpoints` (or `.env`).
- **FlashML FreeVideo (MiniMax H3)**:
  - Add `FAL_KEY` in `⚙️ AI Cores & Endpoints` (or `.env`).
- **Meituan LongCat-Video**:
  - Uses the public Hugging Face Space endpoint automatically or your Colab tunnel.

---

### Method 4: 100% Local Programmatic 2D/3D Animations
No internet or cloud credits required:
- Mental Math & Equations (`short-2-math`)
- Dev Console & Git Reflog (`short-4-git`)
- 3D Cartoon Storybook (`short-7-kids`)
- Finance & Compounding Fees (`short-10-fees`)
- Astronomy & Space Orbit (`short-12-orbit`)
- Vox Paper Collage Documentary (`vox-1-coffee`)

---

## 📁 Source Code Integration Map

- [server.py](file:///d:/Antigravity_Projects/VideoGenerator/server.py): Core HTTP and API backend with config persistence, video uploads, Kokoro TTS orchestration, and compositor dispatch.
- [web/index.html](file:///d:/Antigravity_Projects/VideoGenerator/web/index.html): Modern prompt-first web interface with video dropzone, engine selector, and live settings modal.
- [tools/gen_hunyuan.py](file:///d:/Antigravity_Projects/VideoGenerator/tools/gen_hunyuan.py): Tencent HunyuanVideo generation client (Colab tunnel, Fal.ai, Replicate).
- [tools/gen_freevideo.py](file:///d:/Antigravity_Projects/VideoGenerator/tools/gen_freevideo.py): FlashML FreeVideo MiniMax H3 client (Colab tunnel, Local CLI, Fal.ai).
- [tools/gen_longcat.py](file:///d:/Antigravity_Projects/VideoGenerator/tools/gen_longcat.py): Meituan LongCat-Video client (Colab tunnel, Hugging Face).
- [tools/video_compositor.py](file:///d:/Antigravity_Projects/VideoGenerator/tools/video_compositor.py): Universal FFmpeg compositor that scales to 1080×1920 9:16, burns kinetic ASS subtitles, and mixes voiceover + SFX.
- [colab/VideoAI_Unified_Studio.ipynb](file:///d:/Antigravity_Projects/VideoGenerator/colab/VideoAI_Unified_Studio.ipynb): Free Colab notebook for running all three models on cloud T4/A100 GPUs.
