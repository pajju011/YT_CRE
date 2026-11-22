import base64
import http.server
import json
import mimetypes
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.parse

ROOT = Path(__file__).resolve().parent
PORT = 5000
STUDIO_PROCESS = None

def load_env_dict():
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

def save_env_dict(updates):
    p = ROOT / ".env"
    lines = []
    existing_keys = set()
    if p.exists():
        with open(p, encoding="utf-8") as f:
            lines = f.readlines()
    
    new_lines = []
    for line in lines:
        sline = line.strip()
        if sline and not sline.startswith("#") and "=" in sline:
            k, _ = sline.split("=", 1)
            k = k.strip()
            existing_keys.add(k)
            if k in updates and updates[k] is not None:
                new_lines.append(f"{k}={updates[k]}\n")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
            
    for k, v in updates.items():
        if k not in existing_keys and v is not None:
            new_lines.append(f"{k}={v}\n")
            
    with open(p, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

class StudioRequestHandler(http.server.BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        sys.stderr.write(f"[{self.log_date_time_string()}] {format % args}\n")

    def send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def parse_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            raw = self.rfile.read(content_length).decode("utf-8")
            return json.loads(raw)
        return {}

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/api/projects":
            self.handle_get_projects()
        elif path == "/api/project":
            proj_id = query.get("id", [""])[0]
            self.handle_get_project(proj_id)
        elif path == "/api/config":
            self.handle_get_config()
        elif path == "/api/voices":
            self.handle_get_voices()
        elif path == "/api/personas":
            self.handle_get_personas()
        elif path == "/api/music-beds":
            self.handle_get_music_beds()
        elif path == "/api/sfx-catalog":
            self.handle_get_sfx_catalog()
        elif path == "/api/freefield/status":
            self.handle_get_freefield_status()
        elif path == "/api/freefield/apps":
            self.handle_get_freefield_apps()
        elif path == "/api/cinema/metadata":
            self.handle_get_cinema_metadata()
        elif path == "/api/faceswap/presets":
            self.handle_get_faceswap_presets()
        elif path == "/" or path == "/index.html":
            self.serve_file(ROOT / "web/index.html")
        else:
            local_path = (ROOT / path.lstrip("/")).resolve()
            if local_path.is_file() and str(local_path).startswith(str(ROOT)):
                self.serve_file(local_path)
            else:
                self.send_error(404, "File Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        try:
            body = self.parse_body()
            if path == "/api/save-beats":
                self.handle_save_beats(body)
            elif path == "/api/generate-voice":
                self.handle_generate_voice(body)
            elif path == "/api/sync-captions":
                self.handle_sync_captions(body)
            elif path == "/api/render":
                self.handle_render(body)
            elif path == "/api/mix-sfx":
                self.handle_mix_sfx(body)
            elif path == "/api/youtube-upload":
                self.handle_youtube_upload(body)
            elif path == "/api/create-short":
                self.handle_create_short(body)
            elif path == "/api/start-studio":
                self.handle_start_studio(body)
            elif path == "/api/config":
                self.handle_save_config(body)
            elif path == "/api/upload-video":
                self.handle_upload_video(body)
            elif path == "/api/storyboard/decompose":
                self.handle_storyboard_decompose(body)
            elif path == "/api/freefield/start":
                self.handle_start_freefield(body)
            elif path == "/api/faceswap/swap-image":
                self.handle_faceswap_image(body)
            elif path == "/api/faceswap/swap-video":
                self.handle_faceswap_video(body)
            elif path == "/api/generate-from-prompt":
                self.handle_generate_from_prompt(body)
            else:
                self.send_error(404, "Unknown API endpoint")
        except Exception as e:
            self.send_json({"ok": False, "error": str(e)}, status=500)

    # -------------------------------------------------------------------------
    # CONFIG & UPLOAD HANDLERS
    # -------------------------------------------------------------------------

    def handle_get_config(self):
        env = load_env_dict()
        def mask(val):
            if not val:
                return ""
            if len(val) <= 8:
                return val[:2] + "****"
            return val[:4] + "****" + val[-4:]

        self.send_json({
            "ok": True,
            "colabEndpoint": env.get("COLAB_VIDEO_ENDPOINT", ""),
            "hunyuanEndpoint": env.get("HUNYUAN_ENDPOINT", ""),
            "freevideoEndpoint": env.get("FREEVIDEO_ENDPOINT", ""),
            "longcatEndpoint": env.get("LONGCAT_ENDPOINT", ""),
            "hasFalKey": bool(env.get("FAL_KEY")),
            "falKeyMasked": mask(env.get("FAL_KEY")),
            "hasReplicateToken": bool(env.get("REPLICATE_API_TOKEN")),
            "replicateTokenMasked": mask(env.get("REPLICATE_API_TOKEN")),
            "hasMaiTokenKey": bool(env.get("MAITOKEN_API_KEY")),
            "maiTokenKeyMasked": mask(env.get("MAITOKEN_API_KEY")),
            "hasComfyKey": bool(env.get("COMFY_API_KEY")),
            "comfyKeyMasked": mask(env.get("COMFY_API_KEY"))
        })

    def handle_save_config(self, body):
        updates = {}
        for key in ["COLAB_VIDEO_ENDPOINT", "HUNYUAN_ENDPOINT", "FREEVIDEO_ENDPOINT", "LONGCAT_ENDPOINT", "FAL_KEY", "REPLICATE_API_TOKEN", "MAITOKEN_API_KEY", "COMFY_API_KEY"]:
            if key in body and body[key] != "":
                updates[key] = body[key]
        if updates:
            save_env_dict(updates)
        self.send_json({"ok": True, "message": "Settings updated successfully."})

    def handle_get_voices(self):
        try:
            from tools.gen_voice_multilingual import CURATED_VOICES
            self.send_json({
                "ok": True,
                "kokoro": [
                    {"id": "af_heart", "name": "Heart (Natural Female)", "lang": "English (US)"},
                    {"id": "am_adam", "name": "Adam (Deep Male)", "lang": "English (US)"},
                    {"id": "af_bella", "name": "Bella (Warm Female)", "lang": "English (US)"},
                    {"id": "am_michael", "name": "Michael (Clear Male)", "lang": "English (US)"}
                ],
                "multilingual": CURATED_VOICES
            })
        except Exception as e:
            self.send_json({"ok": False, "error": str(e)}, status=500)

    def handle_get_personas(self):
        try:
            from tools.character_consistency import get_available_personas
            self.send_json({"ok": True, "personas": get_available_personas()})
        except Exception as e:
            self.send_json({"ok": False, "error": str(e)}, status=500)

    def handle_get_music_beds(self):
        try:
            from tools.audio_ducker import get_available_music_beds
            self.send_json({"ok": True, "beds": get_available_music_beds()})
        except Exception as e:
            self.send_json({"ok": False, "error": str(e)}, status=500)

    def handle_get_sfx_catalog(self):
        try:
            from tools.auto_sound_designer import get_available_sfx
            self.send_json({"ok": True, "sfx": get_available_sfx()})
        except Exception as e:
            self.send_json({"ok": False, "error": str(e)}, status=500)

    def handle_get_freefield_status(self):
        try:
            from tools import freefield_bridge
            running = freefield_bridge.is_freefield_running()
            self.send_json({
                "ok": True,
                "running": running,
                "url": freefield_bridge.FREEFIELD_URL,
                "appsCount": 120
            })
        except Exception as e:
            self.send_json({"ok": False, "error": str(e)}, status=500)

    def handle_get_freefield_apps(self):
        try:
            from tools import freefield_bridge
            apps = freefield_bridge.get_freefield_catalog()
            self.send_json({"ok": True, "apps": apps, "count": len(apps)})
        except Exception as e:
            self.send_json({"ok": False, "error": str(e)}, status=500)

    def handle_start_freefield(self, body):
        try:
            from tools import freefield_bridge
            res = freefield_bridge.start_freefield_server()
            self.send_json(res)
        except Exception as e:
            self.send_json({"ok": False, "error": str(e)}, status=500)

    def handle_get_cinema_metadata(self):
        try:
            from tools import cinema_studio
            self.send_json({
                "ok": True,
                "camera_moves": [{"id": k, "name": v["name"], "desc": v["desc"]} for k, v in cinema_studio.CAMERA_MOVES.items()],
                "genres": [{"id": k, "name": k.title()} for k in cinema_studio.GENRES.keys()],
                "eras": [{"id": k, "name": k.title()} for k in cinema_studio.ERAS.keys()],
                "cameras": [{"id": k, "name": k.replace("_", " ").title()} for k in cinema_studio.CAMERAS.keys()],
                "lenses": [{"id": k, "name": k.replace("_", " ").title()} for k in cinema_studio.LENSES.keys()],
                "lightings": [{"id": k, "name": k.replace("_", " ").title()} for k in cinema_studio.LIGHTINGS.keys()],
                "palettes": [{"id": k, "name": k.replace("_", " ").title()} for k in cinema_studio.PALETTES.keys()],
                "presets": cinema_studio.CINEMA_PRESETS
            })
        except Exception as e:
            self.send_json({"ok": False, "error": str(e)}, status=500)

    def handle_get_faceswap_presets(self):
        try:
            from tools import face_swap_engine
            presets = []
            for k, v in face_swap_engine.PRESET_TARGETS.items():
                img_url = ""
                p = Path(v["image_path"])
                if p.exists():
                    img_url = "/" + str(p.relative_to(ROOT)).replace("\\", "/")
                vid_url = ""
                if "video_path" in v:
                    vp = Path(v["video_path"])
                    if vp.exists():
                        vid_url = "/" + str(vp.relative_to(ROOT)).replace("\\", "/")
                presets.append({
                    "id": v["id"],
                    "name": v["name"],
                    "category": v.get("category", "3d"),
                    "desc": v.get("desc", ""),
                    "imageUrl": img_url,
                    "videoUrl": vid_url
                })
            self.send_json({"ok": True, "presets": presets})
        except Exception as e:
            self.send_json({"ok": False, "error": str(e)}, status=500)

    def handle_faceswap_image(self, body):
        try:
            from tools import face_swap_engine
            source_path = body.get("sourceImage")
            target_preset = body.get("targetPreset", "dancing_girl")
            target_path = body.get("targetImage")
            color_correct = body.get("colorCorrect", True)

            if not source_path:
                source_path = str(ROOT / "media" / "projects" / "dancing-girl" / "b2-dance.png")
            else:
                source_path = str((ROOT / source_path.lstrip("/")).resolve())

            if not target_path or not Path(target_path).exists():
                preset_info = face_swap_engine.PRESET_TARGETS.get(target_preset, face_swap_engine.PRESET_TARGETS["dancing_girl"])
                target_path = preset_info["image_path"]

            target_path = str((ROOT / target_path.lstrip("/")).resolve()) if not Path(target_path).is_absolute() else str(target_path)

            out_dir = ROOT / "shorts" / "faceswap-results"
            out_dir.mkdir(parents=True, exist_ok=True)
            timestamp = int(time.time())
            out_file = out_dir / f"swap_{timestamp}.jpg"

            res = face_swap_engine.swap_face_cv(
                Path(source_path),
                Path(target_path),
                out_file,
                color_correct=color_correct
            )
            if res.get("ok"):
                url = "/" + str(out_file.relative_to(ROOT)).replace("\\", "/")
                self.send_json({"ok": True, "url": url, "details": res})
            else:
                self.send_json(res, status=400)
        except Exception as e:
            self.send_json({"ok": False, "error": str(e)}, status=500)

    def handle_faceswap_video(self, body):
        try:
            from tools import video_face_swapper, face_swap_engine
            source_path = body.get("sourceImage")
            target_preset = body.get("targetPreset", "dancing_girl")
            target_path = body.get("targetVideo")
            duration = body.get("duration", 4.0)

            if not source_path:
                source_path = str(ROOT / "media" / "projects" / "dancing-girl" / "b2-dance.png")
            else:
                source_path = str((ROOT / source_path.lstrip("/")).resolve())

            if not target_path or not Path(target_path).exists():
                preset_info = face_swap_engine.PRESET_TARGETS.get(target_preset, face_swap_engine.PRESET_TARGETS["dancing_girl"])
                target_path = preset_info.get("video_path") or str(ROOT / "shorts" / "short-storyboard" / "scenes" / "scene_01.mp4")

            target_path = str((ROOT / target_path.lstrip("/")).resolve()) if not Path(target_path).is_absolute() else str(target_path)

            out_dir = ROOT / "shorts" / "faceswap-results"
            out_dir.mkdir(parents=True, exist_ok=True)
            timestamp = int(time.time())
            out_file = out_dir / f"swap_video_{timestamp}.mp4"

            res = video_face_swapper.swap_face_in_video(
                Path(source_path),
                Path(target_path),
                out_file,
                max_duration=float(duration) if duration else None
            )
            if res.get("ok"):
                url = "/" + str(out_file.relative_to(ROOT)).replace("\\", "/")
                self.send_json({"ok": True, "url": url, "details": res})
            else:
                self.send_json(res, status=400)
        except Exception as e:
            self.send_json({"ok": False, "error": str(e)}, status=500)

    def handle_storyboard_decompose(self, body):
        try:
            from tools.storyboard_engine import decompose_story
            from tools.character_consistency import BUILTIN_PERSONAS
            prompt = body.get("prompt", "Adventures in the crystal cave")
            persona_id = body.get("persona", "3d_cartoon")
            scenes_count = int(body.get("scenesCount", 4))
            p_info = BUILTIN_PERSONAS.get(persona_id, BUILTIN_PERSONAS["3d_cartoon"])
            scenes = decompose_story(prompt, p_info["name"], scenes_count)
            self.send_json({"ok": True, "scenes": scenes, "persona": p_info})
        except Exception as e:
            self.send_json({"ok": False, "error": str(e)}, status=500)

    def handle_upload_video(self, body):
        filename = body.get("filename", "uploaded_clip.mp4")
        base64_data = body.get("data", "")
        if "," in base64_data:
            base64_data = base64_data.split(",", 1)[1]

        safe_name = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', filename)
        ts = int(time.time())
        dest_name = f"{ts}_{safe_name}"
        dest_path = ROOT / "media" / "uploads" / dest_name
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        raw_bytes = base64.b64decode(base64_data)
        with open(dest_path, "wb") as f:
            f.write(raw_bytes)

        rel_url = f"/media/uploads/{dest_name}"
        self.send_json({
            "ok": True,
            "filename": dest_name,
            "videoUrl": rel_url,
            "path": str(dest_path.relative_to(ROOT)).replace("\\", "/")
        })

    # -------------------------------------------------------------------------
    # API HANDLERS
    # -------------------------------------------------------------------------

    def get_project_dir(self, proj_id):
        candidates = [
            ROOT / "shorts" / proj_id,
            ROOT / "ai-shorts" / proj_id,
            ROOT / "vox-shorts" / proj_id,
        ]
        for c in candidates:
            if c.exists() and c.is_dir():
                return c
        return None

    def handle_get_projects(self):
        projects = []
        scan_dirs = [
            (ROOT / "shorts", "tsx"),
            (ROOT / "ai-shorts", "generative"),
            (ROOT / "vox-shorts", "vox")
        ]

        for base_dir, track in scan_dirs:
            if not base_dir.exists():
                continue
            for item in sorted(base_dir.iterdir()):
                if item.is_dir() and not item.name.startswith("."):
                    beats_file = item / "beats.json"
                    scenes_file = item / "scenes.json"
                    target_file = beats_file if beats_file.exists() else (scenes_file if scenes_file.exists() else None)
                    
                    title = item.name
                    duration_sec = 42
                    comp_id = ""

                    if target_file:
                        try:
                            with open(target_file, encoding="utf-8") as f:
                                data = json.load(f)
                                title = data.get("title", title)
                                duration_sec = data.get("format", {}).get("durationSec", 42)
                                comp_id = data.get("composition", "")
                        except Exception:
                            pass

                    voice_file = item / "output" / "kokoro" / "voice.wav"
                    has_voice = voice_file.exists()

                    has_video = False
                    output_dir = item / "output"
                    if output_dir.exists():
                        has_video = any(output_dir.glob("*.mp4"))

                    projects.append({
                        "id": item.name,
                        "title": title,
                        "track": track,
                        "durationSec": duration_sec,
                        "composition": comp_id,
                        "hasVoice": has_voice,
                        "hasVideo": has_video,
                        "path": str(item.relative_to(ROOT)).replace("\\", "/")
                    })

        self.send_json({"ok": True, "projects": projects})

    def handle_get_project(self, proj_id):
        pdir = self.get_project_dir(proj_id)
        if not pdir:
            self.send_json({"ok": False, "error": f"Project {proj_id} not found"}, status=404)
            return

        beats_file = pdir / "beats.json"
        scenes_file = pdir / "scenes.json"
        manifest_file = beats_file if beats_file.exists() else scenes_file

        data = {}
        if manifest_file and manifest_file.exists():
            with open(manifest_file, encoding="utf-8") as f:
                data = json.load(f)

        script_file = pdir / "script.md"
        script_text = script_file.read_text(encoding="utf-8") if script_file.exists() else ""

        self.send_json({
            "ok": True,
            "id": proj_id,
            "manifest": data,
            "script": script_text
        })

    def handle_save_beats(self, body):
        proj_id = body.get("id")
        beats = body.get("beats")
        pdir = self.get_project_dir(proj_id)
        if not pdir or not beats:
            self.send_json({"ok": False, "error": "Invalid project or payload"}, status=400)
            return

        beats_file = pdir / "beats.json"
        with open(beats_file, "w", encoding="utf-8") as f:
            json.dump(beats, f, indent=2, ensure_ascii=False)

        self.send_json({"ok": True, "message": "beats.json updated"})

    def handle_generate_voice(self, body):
        proj_id = body.get("id")
        voice = body.get("voice", "af_heart")
        speed = float(body.get("speed", 1.0))
        pdir = self.get_project_dir(proj_id)
        if not pdir:
            self.send_json({"ok": False, "error": f"Project {proj_id} not found"}, status=404)
            return

        rel_proj = str(pdir.relative_to(ROOT)).replace("\\", "/")
        cmd = [sys.executable, str(ROOT / "tools" / "gen_voice_kokoro.py"), "--project", rel_proj, "--voice", voice, "--speed", str(speed)]
        res = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
        if res.returncode == 0:
            self.send_json({"ok": True, "message": "Voice generated successfully"})
        else:
            self.send_json({"ok": False, "error": res.stderr or res.stdout}, status=500)

    def handle_sync_captions(self, body):
        proj_id = body.get("id")
        pdir = self.get_project_dir(proj_id)
        if not pdir:
            self.send_json({"ok": False, "error": f"Project {proj_id} not found"}, status=404)
            return

        rel_proj = str(pdir.relative_to(ROOT)).replace("\\", "/")
        cmd = [sys.executable, str(ROOT / "tools" / "update_kokoro_captions.py"), "--project", rel_proj]
        res = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
        if res.returncode == 0:
            self.send_json({"ok": True, "message": "Captions synced into vo.gen.ts"})
        else:
            self.send_json({"ok": False, "error": res.stderr or res.stdout}, status=500)

    def handle_render(self, body):
        proj_id = body.get("id")
        comp_id = body.get("composition")
        pdir = self.get_project_dir(proj_id)

        remotion_dir = ROOT / "remotion"
        npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"

        render_args = [npm_cmd, "run", "render"]
        if comp_id:
            render_args.extend(["--", comp_id])

        res = subprocess.run(render_args, cwd=str(remotion_dir), capture_output=True, text=True)
        if res.returncode == 0:
            self.send_json({"ok": True, "message": "Render completed", "output": res.stdout})
        else:
            self.send_json({"ok": False, "error": res.stderr or res.stdout}, status=500)

    def handle_mix_sfx(self, body):
        proj_id = body.get("id")
        pdir = self.get_project_dir(proj_id)
        if not pdir:
            self.send_json({"ok": False, "error": f"Project {proj_id} not found"}, status=404)
            return

        rel_proj = str(pdir.relative_to(ROOT)).replace("\\", "/")
        cmd = [sys.executable, str(ROOT / "tools" / "mix_sfx.py"), rel_proj]
        res = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
        if res.returncode == 0:
            self.send_json({"ok": True, "message": "SFX mixed successfully", "output": res.stdout})
        else:
            self.send_json({"ok": False, "error": res.stderr or res.stdout}, status=500)

    def handle_youtube_upload(self, body):
        title = body.get("title", "AI Generated Short")
        cmd = [sys.executable, str(ROOT / "upload_youtube.py"), "--title", title]
        res = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
        if res.returncode == 0:
            self.send_json({"ok": True, "message": "Uploaded to YouTube!", "output": res.stdout})
        else:
            self.send_json({"ok": False, "error": res.stderr or res.stdout}, status=500)

    def handle_create_short(self, body):
        title = body.get("title", "New AI Short")
        track = body.get("track", "shorts")
        safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '', title.lower().replace(" ", "-"))
        new_id = f"short-{int(time.time() % 10000)}-{safe_name}"

        target_dir = ROOT / track / new_id
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "output" / "kokoro").mkdir(parents=True, exist_ok=True)

        template_beats = {
            "id": new_id,
            "title": title,
            "composition": "".join(w.capitalize() for w in re.split(r"[-_]", new_id)),
            "format": {
                "width": 1080,
                "height": 1920,
                "fps": 30,
                "durationSec": 42
            },
            "vo": [
                { "beat": "hook", "text": f"{title}. Watch this trick.", "start": 0.4, "end": 3.2 },
                { "beat": "setup", "text": "Normally this takes paper and ten seconds.", "start": 3.5, "end": 7.0 },
                { "beat": "quiz", "text": "Can you calculate the answer in your head?", "start": 7.2, "end": 12.0 },
                { "beat": "reveal", "text": "Here is the shortcut. Separate the digits and add them.", "start": 12.5, "end": 20.0 },
                { "beat": "twist", "text": "And it works for any two-digit number instantly.", "start": 20.5, "end": 30.0 },
                { "beat": "loop", "text": "Try it right now with sixty-three times eleven.", "start": 30.5, "end": 40.0 }
            ]
        }

        with open(target_dir / "beats.json", "w", encoding="utf-8") as f:
            json.dump(template_beats, f, indent=2, ensure_ascii=False)

        (target_dir / "script.md").write_text(f"# {title}\n\nGenerated via VideoGenerator Studio.\n", encoding="utf-8")
        self.send_json({"ok": True, "message": f"Created short {new_id}"})

    def handle_start_studio(self, body):
        global STUDIO_PROCESS
        remotion_dir = ROOT / "remotion"
        npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"

        if "STUDIO_PROCESS" not in globals() or STUDIO_PROCESS is None or STUDIO_PROCESS.poll() is not None:
            STUDIO_PROCESS = subprocess.Popen([npm_cmd, "run", "studio"], cwd=str(remotion_dir))

        self.send_json({"ok": True, "url": "http://localhost:3000", "message": "Remotion Studio launching at http://localhost:3000"})

    def handle_generate_from_prompt(self, body):
        prompt = body.get("prompt", "").lower().strip()
        category = body.get("category", "math").lower()
        voice = body.get("voice", "af_heart")
        speed = float(body.get("speed", 1.0))
        sfx = body.get("sfx", True)
        music = body.get("music", "lofi-warm")
        captions = bool(body.get("captions", False))  # Default False: don't create captions for all videos
        imported_video_path = body.get("videoPath")

        def matches_any_word(words, text):
            pattern = r'\b(' + '|'.join(re.escape(w) for w in words) + r')\b'
            return bool(re.search(pattern, text, re.IGNORECASE))

        is_generative_prompt = matches_any_word([
            "dance", "dancing", "girl", "cartoon", "3d", "character", "cute", 
            "kid", "kids", "story", "animation", "pip", "fox", "magic", "monster"
        ], prompt) or category in ["generative", "story", "kids", "hunyuan", "freevideo", "longcat"]

        custom_title = None
        custom_vo = None

        if category == "hunyuan":
            proj_id = "short-7-kids"
            custom_title = "Tencent HunyuanVideo Generation"
            custom_vo = [
                {"beat": "hook", "text": "Generated with Tencent HunyuanVideo. Watch the full animation.", "start": 0.4, "end": 4.5},
                {"beat": "setup", "text": "Rendering 3D motion dynamics using Tencent's 13B foundation model.", "start": 4.8, "end": 9.0},
                {"beat": "reveal", "text": "Smooth frame-by-frame character animation with rich details.", "start": 9.2, "end": 14.5},
                {"beat": "loop", "text": "Experience open-source generative video created right on your PC.", "start": 14.8, "end": 19.0}
            ]
        elif category == "freevideo":
            proj_id = "short-7-kids"
            custom_title = "FlashML FreeVideo (MiniMax H3)"
            custom_vo = [
                {"beat": "hook", "text": "Rendered with FlashML FreeVideo and the MiniMax H3 engine.", "start": 0.4, "end": 4.5},
                {"beat": "setup", "text": "High-efficiency local video generation built for consumer hardware.", "start": 4.8, "end": 9.0},
                {"beat": "reveal", "text": "Notice the smooth character movement and dynamic camera flow.", "start": 9.2, "end": 14.5},
                {"beat": "loop", "text": "Create your next viral short with open source AI video.", "start": 14.8, "end": 19.0}
            ]
        elif category == "longcat":
            proj_id = "short-7-kids"
            custom_title = "Meituan LongCat-Video"
            custom_vo = [
                {"beat": "hook", "text": "Powered by Meituan LongCat-Video foundation model.", "start": 0.4, "end": 4.5},
                {"beat": "setup", "text": "Unifying text-to-video and audio-driven avatar synchronization.", "start": 4.8, "end": 9.0},
                {"beat": "reveal", "text": "Long-form temporal consistency with zero color drift.", "start": 9.2, "end": 14.5},
                {"beat": "loop", "text": "Watch this adorable character animation loop again from the start.", "start": 14.8, "end": 19.0}
            ]
        elif matches_any_word(["dance", "dancing", "girl", "moves", "smile", "smiling"], prompt):
            proj_id = "short-14-dance"
            custom_title = "Cute 3D Dancing Girl"
            custom_vo = [
                {"beat": "hook", "text": "Look at her dance! She has the sweetest rhythm in the world.", "start": 0.3, "end": 3.8},
                {"beat": "setup", "text": "Moving her hands and tapping her feet to the cheerful music.", "start": 4.0, "end": 7.8},
                {"beat": "reveal", "text": "Spinning around with the brightest smile you have ever seen!", "start": 8.0, "end": 11.8},
                {"beat": "loop", "text": "Strike a happy pose and let's dance all over again!", "start": 12.0, "end": 15.0}
            ]
        elif is_generative_prompt or imported_video_path:
            proj_id = "short-7-kids"
            custom_title = "Cute 3D Story Animation"
            custom_vo = [
                {"beat": "hook", "text": "Look at her dance! She has the happiest rhythm in the world.", "start": 0.4, "end": 4.5},
                {"beat": "setup", "text": "Moving her hands and feet to the beat with bright cheerful energy.", "start": 4.8, "end": 9.0},
                {"beat": "quiz", "text": "Can you dance along with these fun 3D animation moves?", "start": 9.2, "end": 13.5},
                {"beat": "reveal", "text": "Step left, step right, and spin with an adorable big smile!", "start": 13.8, "end": 19.5},
                {"beat": "loop", "text": "Now let the music play and start dancing all over again!", "start": 19.8, "end": 25.0}
            ]
        elif matches_any_word(["reflog", "git", "commit", "branch", "terminal"], prompt):
            proj_id = "short-4-git"
        elif matches_any_word(["monty", "door", "probab", "paradox"], prompt):
            proj_id = "short-5-prob"
        elif matches_any_word(["sort", "bubble", "quick", "algo", "array"], prompt):
            proj_id = "short-3-algo"
        elif matches_any_word(["fee", "fees", "retire", "retirement", "invest", "investment", "percent"], prompt):
            proj_id = "short-10-fees"
        elif matches_any_word(["orbit", "astronaut", "space", "weightless", "falling"], prompt):
            proj_id = "short-12-orbit"
        elif matches_any_word(["map", "mercator", "greenland", "africa", "geography"], prompt):
            proj_id = "short-11-map"
        elif matches_any_word(["coffee", "history", "documentary", "vox"], prompt):
            proj_id = "vox-1-coffee"
        elif matches_any_word(["excel", "flash fill", "sheet"], prompt):
            proj_id = "short-6-sheet"
        elif matches_any_word(["phish", "paypal", "url", "security"], prompt):
            proj_id = "short-8-phish"
        elif matches_any_word(["chord", "music", "song", "piano"], prompt):
            proj_id = "short-9-chords"
        elif category == "avatar":
            proj_id = "short-14-dance"
            custom_title = "Talking Avatar"
            custom_vo = [
                {"beat": "speech", "text": prompt if prompt else "Hello! Welcome to our AI video generation studio.", "start": 0.2, "end": 4.5}
            ]
        elif category in ["cinema", "cinema-video"]:
            proj_id = "short-cinema"
            custom_title = "Cinema Studio (Freefield Engine)"
            pdir = ROOT / "shorts" / "short-cinema"
            pdir.mkdir(parents=True, exist_ok=True)
            custom_vo = [
                {"beat": "hook", "text": prompt if prompt else "Cinema Studio in motion.", "start": 0.3, "end": 5.0}
            ]
        elif category == "storyboard":
            proj_id = "short-storyboard"
            custom_title = "Multi-Scene Storyboard"
            pdir = ROOT / "shorts" / "short-storyboard"
            pdir.mkdir(parents=True, exist_ok=True)
            persona_id = body.get("persona", "3d_cartoon")
            scenes_count = int(body.get("scenesCount", 4))
            custom_scenes = body.get("scenes")
            if not custom_scenes:
                from tools.storyboard_engine import decompose_story
                from tools.character_consistency import BUILTIN_PERSONAS
                p_info = BUILTIN_PERSONAS.get(persona_id, BUILTIN_PERSONAS["3d_cartoon"])
                custom_scenes = decompose_story(prompt, p_info["name"], scenes_count)
            custom_vo = [
                {"beat": s.get("beat", f"scene_{i+1}"), "text": s.get("narration", s.get("text", "")), "start": round(i*4.0, 2), "end": round((i+1)*4.0, 2)}
                for i, s in enumerate(custom_scenes)
            ]
        elif matches_any_word(["chess", "checkmate"], prompt):
            proj_id = "short-1-chess"
        else:
            if category == "dev":
                proj_id = "short-4-git"
            elif category == "finance":
                proj_id = "short-10-fees"
            elif category == "science":
                proj_id = "short-12-orbit"
            elif category == "vox":
                proj_id = "vox-1-coffee"
            else:
                proj_id = "short-2-math"

        pdir = self.get_project_dir(proj_id)
        if not pdir:
            pdir = ROOT / "shorts" / "short-2-math"
            proj_id = "short-2-math"

        rel_proj = str(pdir.relative_to(ROOT)).replace("\\", "/")
        py_exe = sys.executable
        venv_py = ROOT / ".venv-kokoro" / "Scripts" / "python.exe"
        if venv_py.exists():
            py_exe = str(venv_py)

        # Apply AI script or tailored custom script
        beats_file = pdir / "beats.json"
        try:
            from tools import maitoken_client
            ai_script = maitoken_client.generate_script(prompt, category)
            if ai_script and "vo" in ai_script and beats_file.exists():
                with open(beats_file, "r", encoding="utf-8") as f:
                    bdata = json.load(f)
                bdata["title"] = ai_script.get("title", bdata.get("title", proj_id))
                bdata["vo"] = ai_script["vo"]
                with open(beats_file, "w", encoding="utf-8") as f:
                    json.dump(bdata, f, indent=2, ensure_ascii=False)
            elif custom_vo and beats_file.exists():
                with open(beats_file, "r", encoding="utf-8") as f:
                    bdata = json.load(f)
                bdata["title"] = custom_title or bdata.get("title", proj_id)
                bdata["vo"] = custom_vo
                with open(beats_file, "w", encoding="utf-8") as f:
                    json.dump(bdata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Scripting Fallback] {e}")

        # 1. Synthesize voice with Kokoro or Edge-TTS (Multi-language)
        voice_out_wav = pdir / "output" / "kokoro" / "voice.wav"
        voice_out_wav.parent.mkdir(parents=True, exist_ok=True)
        is_edge = "-" in voice

        if is_edge:
            full_text = prompt if (category == "avatar" or is_edge) and prompt else (" ".join(item.get("text", "") for item in custom_vo) if custom_vo else prompt)
            timings_json = pdir / "output" / "kokoro" / "timings.json"
            cmd_voice = [
                py_exe, str(ROOT / "tools" / "gen_voice_multilingual.py"),
                "--text", full_text,
                "--voice", voice,
                "--speed", str(speed),
                "--out", str(voice_out_wav),
                "--timings", str(timings_json)
            ]
            subprocess.run(cmd_voice, cwd=str(ROOT), capture_output=True)
            if timings_json.exists():
                try:
                    with open(timings_json, encoding="utf-8") as f_tim:
                        w_list = json.load(f_tim)
                    from tools.gen_voice_multilingual import words_to_vo_beats
                    vo_beats = words_to_vo_beats(w_list)
                    if vo_beats and beats_file.exists():
                        with open(beats_file, "r", encoding="utf-8") as f:
                            bdata = json.load(f)
                        bdata["vo"] = vo_beats
                        bdata["title"] = custom_title or bdata.get("title", proj_id)
                        with open(beats_file, "w", encoding="utf-8") as f:
                            json.dump(bdata, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    print(f"[Timings sync error] {e}")
        else:
            cmd_voice = [py_exe, str(ROOT / "tools" / "gen_voice_kokoro.py"), "--project", rel_proj, "--voice", voice, "--speed", str(speed)]
            subprocess.run(cmd_voice, cwd=str(ROOT), capture_output=True)
            cmd_caps = [py_exe, str(ROOT / "tools" / "update_kokoro_captions.py"), "--project", rel_proj]
            subprocess.run(cmd_caps, cwd=str(ROOT), capture_output=True)

        # 3. Read metadata & script
        beats_file = pdir / "beats.json"
        title = proj_id
        script_text = ""
        if beats_file.exists():
            with open(beats_file, encoding="utf-8") as f:
                bdata = json.load(f)
                title = bdata.get("title", proj_id)
                script_lines = [item.get("text", "") for item in bdata.get("vo", [])]
                script_text = " ".join(script_lines)

        # 4. Generate or Resolve Video File
        video_url = None
        raw_video = None
        balance_note = ""

        out_dir = pdir / "output"
        out_dir.mkdir(parents=True, exist_ok=True)
        final_short_path = out_dir / "final_short.mp4"

        # Check imported video
        if imported_video_path:
            p_imp = (ROOT / imported_video_path.lstrip("/")).resolve()
            if p_imp.exists():
                raw_video = p_imp

        # Check Talking Head Avatar
        avatar_img_path = body.get("avatarPath")
        if not raw_video and (category == "avatar" or avatar_img_path):
            p_img = (ROOT / avatar_img_path.lstrip("/")).resolve() if avatar_img_path else (ROOT / "media" / "projects" / "dancing-girl" / "b1-dance.png")
            out_avatar_mp4 = out_dir / "avatar_raw.mp4"
            cmd_avatar = [
                py_exe, str(ROOT / "tools" / "gen_talking_avatar.py"),
                "--image", str(p_img),
                "--audio", str(voice_out_wav),
                "--out", str(out_avatar_mp4)
            ]
            subprocess.run(cmd_avatar, cwd=str(ROOT), capture_output=True)
            if out_avatar_mp4.exists():
                raw_video = out_avatar_mp4

        # Check Multi-Scene Storyboard
        if not raw_video and category == "storyboard":
            persona_id = body.get("persona", "3d_cartoon")
            scenes_count = int(body.get("scenesCount", 4))
            c_scenes = body.get("scenes") or custom_scenes

            from tools.storyboard_engine import build_storyboard
            res_sb = build_storyboard(prompt, pdir, persona_id=persona_id, scene_count=scenes_count, custom_scenes=c_scenes)
            if res_sb.get("ok"):
                raw_sb_path = Path(res_sb.get("raw_video", ""))
                if raw_sb_path.exists():
                    raw_video = raw_sb_path

        # Check Freefield Cinema Studio & 33 Camera Moves
        if not raw_video and category in ["cinema", "cinema-video"]:
            c_move = body.get("cameraMove", "dolly_in")
            c_genre = body.get("genre", "general")
            c_era = body.get("era", "modern")
            c_camera = body.get("camera", "arri")
            c_lens = body.get("lens", "anamorphic")
            c_lighting = body.get("lighting", "cinematic")
            c_palette = body.get("palette", "teal_orange")

            from tools.cinema_studio import generate_cinema_short
            res_cin = generate_cinema_short(
                prompt, out_dir,
                camera_move=c_move, genre=c_genre, era=c_era,
                camera=c_camera, lens=c_lens, lighting=c_lighting, palette=c_palette
            )
            if res_cin.get("ok"):
                raw_c_path = Path(res_cin["raw_video"])
                if raw_c_path.exists():
                    raw_video = raw_c_path

        # Check HunyuanVideo
        if not raw_video and category == "hunyuan":
            out_hunyuan = out_dir / "hunyuan_raw.mp4"
            cmd_hunyuan = [py_exe, str(ROOT / "tools" / "gen_hunyuan.py"), "--prompt", prompt, "--out", str(out_hunyuan)]
            res_h = subprocess.run(cmd_hunyuan, cwd=str(ROOT), capture_output=True, text=True)
            if out_hunyuan.exists() and res_h.returncode == 0:
                raw_video = out_hunyuan
            else:
                balance_note = "Tencent HunyuanVideo (13B) requires 14GB–45GB VRAM (your GPU has 4GB VRAM). Launch the 1-click Google Colab notebook in `colab/VideoAI_Unified_Studio.ipynb` and enter the tunnel URL in Settings!"

        # Check FreeVideo
        if not raw_video and category == "freevideo":
            out_freevideo = out_dir / "freevideo_raw.mp4"
            cmd_fv = [py_exe, str(ROOT / "tools" / "gen_freevideo.py"), "--prompt", prompt, "--out", str(out_freevideo)]
            res_fv = subprocess.run(cmd_fv, cwd=str(ROOT), capture_output=True, text=True)
            if out_freevideo.exists() and res_fv.returncode == 0:
                raw_video = out_freevideo
            else:
                balance_note = "FlashML FreeVideo (MiniMax H3) requires 8GB+ VRAM (your GPU has 4GB VRAM). Connect the 1-click Google Colab notebook in `colab/VideoAI_Unified_Studio.ipynb` or add FAL_KEY in Settings!"

        # Check LongCat-Video
        if not raw_video and category == "longcat":
            out_longcat = out_dir / "longcat_raw.mp4"
            cmd_lc = [py_exe, str(ROOT / "tools" / "gen_longcat.py"), "--prompt", prompt, "--out", str(out_longcat)]
            res_lc = subprocess.run(cmd_lc, cwd=str(ROOT), capture_output=True, text=True)
            if out_longcat.exists() and res_lc.returncode == 0:
                raw_video = out_longcat
            else:
                balance_note = "Meituan LongCat-Video (13.6B) requires 16GB+ VRAM (your GPU has 4GB VRAM). Connect the 1-click Google Colab notebook in `colab/VideoAI_Unified_Studio.ipynb` or use HuggingFace Spaces!"

        # Check MaiToken Seedance
        if not raw_video and category == "generative":
            balance_note = "Your MaiToken balance is 0.00 credits. Use the free Google Colab Hub or drag-and-drop any MP4 video below to add AI voice and captions!"

        # Check Comfy Router (Wan 2.5 / Kling)
        if not raw_video and category in ["wan", "kling"]:
            out_comfy = out_dir / f"{category}_raw.mp4"
            from tools import comfy_client
            model_name = "kling/kling-3.0-turbo" if category == "kling" else "wan/wan2.5-t2v-preview"
            res_cf = comfy_client.generate_video(prompt, out_comfy, model=model_name)
            if res_cf.get("ok") and out_comfy.exists():
                raw_video = out_comfy
            else:
                balance_note = res_cf.get("error") or "Comfy Router: Insufficient credits. Top up at platform.comfy.org or use the free Storyboard Studio!"

        # 5. Universal Video Compositor Pass (Composite Raw Video + Voice + Ducked Music + SFX + Captions)
        voice_wav = pdir / "output" / "kokoro" / "voice.wav"
        if raw_video and raw_video.exists() and voice_wav.exists():
            cmd_comp = [
                py_exe, str(ROOT / "tools" / "video_compositor.py"),
                "--video", str(raw_video),
                "--audio", str(voice_wav),
                "--beats", str(beats_file),
                "--out", str(final_short_path),
                "--music", str(music)
            ]
            if sfx:
                cmd_comp.append("--sfx")
            else:
                cmd_comp.append("--no-sfx")
            if captions:
                cmd_comp.append("--captions")
            else:
                cmd_comp.append("--no-captions")

            res_c = subprocess.run(cmd_comp, cwd=str(ROOT), capture_output=True, text=True)
            if res_c.returncode == 0 and final_short_path.exists():
                video_url = "/" + str(final_short_path.relative_to(ROOT)).replace("\\", "/")

        # 6. Video resolution from rendered outputs
        if not video_url:
            mp4s = list(out_dir.glob("final_short.mp4")) or list(out_dir.glob("*-final.mp4")) or list(out_dir.glob("*-sfx.mp4")) or list(out_dir.glob("*.mp4"))
            if mp4s:
                video_url = "/" + str(mp4s[0].relative_to(ROOT)).replace("\\", "/")
            else:
                rem_candidates = list((ROOT / "remotion" / "out").glob(f"*{proj_id.replace('-', '')}*.mp4"))
                if rem_candidates:
                    video_url = "/" + str(rem_candidates[0].relative_to(ROOT)).replace("\\", "/")

        if video_url:
            balance_note = ""

        voice_url = "/" + rel_proj + "/output/kokoro/voice.wav"

        self.send_json({
            "ok": True,
            "id": proj_id,
            "title": title,
            "script": script_text,
            "videoUrl": video_url,
            "voiceUrl": voice_url,
            "note": balance_note
        })

    # -------------------------------------------------------------------------
    # STATIC FILE SERVING WITH RANGE SUPPORT (FOR VIDEO SEEKING)
    # -------------------------------------------------------------------------

    def serve_file(self, file_path: Path):
        try:
            file_size = file_path.stat().st_size
            content_type, _ = mimetypes.guess_type(str(file_path))
            if not content_type:
                content_type = "application/octet-stream"

            range_header = self.headers.get("Range")
            if range_header and range_header.startswith("bytes="):
                byte_range = range_header.replace("bytes=", "").split("-")
                start = int(byte_range[0]) if byte_range[0] else 0
                end = int(byte_range[1]) if len(byte_range) > 1 and byte_range[1] else file_size - 1
                length = end - start + 1

                self.send_response(206)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Content-Length", str(length))
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

                with open(file_path, "rb") as f:
                    f.seek(start)
                    self.wfile.write(f.read(length))
            else:
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(file_size))
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
        except Exception as e:
            self.send_error(500, f"Error streaming file: {e}")

def run_server():
    server_address = ("127.0.0.1", PORT)
    httpd = http.server.ThreadingHTTPServer(server_address, StudioRequestHandler)
    print("=" * 60)
    print(f"🎬 VideoGenerator Web Studio running at: http://localhost:{PORT}")
    print("=" * 60)
    print("Supported AI Video Cores:")
    print("  • Tencent HunyuanVideo (13B)")
    print("  • FlashML FreeVideo (MiniMax H3)")
    print("  • Meituan LongCat-Video (13.6B)")
    print("  • Kokoro Local Neural TTS")
    print("  • Remotion Kinetic Programmatic Shorts")
    print("=" * 60)
    print("Open your browser and navigate to http://localhost:5000\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
