import http.server
import json
import mimetypes
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.parse

ROOT = Path(__file__).resolve().parent
PORT = 5000

class StudioRequestHandler(http.server.BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        # Clean logging
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

        # Route API endpoints
        if path == "/api/projects":
            self.handle_get_projects()
        elif path == "/api/project":
            proj_id = query.get("id", [""])[0]
            self.handle_get_project(proj_id)
        elif path == "/" or path == "/index.html":
            self.serve_file(ROOT / "web/index.html")
        else:
            # Static file serving
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
            elif path == "/api/generate-from-prompt":
                self.handle_generate_from_prompt(body)
            else:
                self.send_error(404, "Unknown API endpoint")
        except Exception as e:
            self.send_json({"ok": False, "error": str(e)}, status=500)

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

                    # Detect existing voice & video
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
                        "relPath": str(item.relative_to(ROOT)).replace("\\", "/")
                    })

        self.send_json(projects)

    def handle_get_project(self, proj_id):
        pdir = self.get_project_dir(proj_id)
        if not pdir:
            self.send_json({"error": "Project not found"}, status=404)
            return

        beats_file = pdir / "beats.json"
        beats_data = {}
        if beats_file.exists():
            with open(beats_file, encoding="utf-8") as f:
                beats_data = json.load(f)

        # Find voice file
        voice_url = None
        voice_file = pdir / "output" / "kokoro" / "voice.wav"
        if voice_file.exists():
            voice_url = "/" + str(voice_file.relative_to(ROOT)).replace("\\", "/")

        # Find video file
        video_url = None
        output_dir = pdir / "output"
        if output_dir.exists():
            mp4s = list(output_dir.glob("*-final.mp4")) or list(output_dir.glob("*-sfx.mp4")) or list(output_dir.glob("*.mp4"))
            if mp4s:
                video_url = "/" + str(mp4s[0].relative_to(ROOT)).replace("\\", "/")

        # Fallback to remotion/out
        if not video_url and beats_data.get("composition"):
            comp = beats_data["composition"]
            remotion_mp4 = ROOT / "remotion" / "out" / f"{comp}.mp4"
            remotion_voiced = ROOT / "remotion" / "out" / f"{comp}-voiced.mp4"
            if remotion_voiced.exists():
                video_url = "/" + str(remotion_voiced.relative_to(ROOT)).replace("\\", "/")
            elif remotion_mp4.exists():
                video_url = "/" + str(remotion_mp4.relative_to(ROOT)).replace("\\", "/")

        self.send_json({
            "id": proj_id,
            "title": beats_data.get("title", proj_id),
            "durationSec": beats_data.get("format", {}).get("durationSec", 42),
            "composition": beats_data.get("composition", ""),
            "beats": beats_data,
            "voiceUrl": voice_url,
            "videoUrl": video_url,
            "path": str(pdir.relative_to(ROOT)).replace("\\", "/")
        })

    def handle_save_beats(self, body):
        proj_id = body.get("id")
        beats = body.get("beats")
        pdir = self.get_project_dir(proj_id)
        if not pdir or not beats:
            self.send_json({"ok": False, "error": "Invalid request"}, status=400)
            return

        beats_file = pdir / "beats.json"
        with open(beats_file, "w", encoding="utf-8") as f:
            json.dump(beats, f, indent=2, ensure_ascii=False)

        self.send_json({"ok": True, "message": "beats.json saved"})

    def handle_generate_voice(self, body):
        proj_id = body.get("id")
        pdir = self.get_project_dir(proj_id)
        if not pdir:
            self.send_json({"ok": False, "error": "Project not found"}, status=404)
            return

        rel_proj = str(pdir.relative_to(ROOT)).replace("\\", "/")
        py_exe = sys.executable

        # 1. Run Kokoro voice generator
        cmd1 = [py_exe, str(ROOT / "tools" / "gen_voice_kokoro.py"), "--project", rel_proj]
        res1 = subprocess.run(cmd1, capture_output=True, text=True, cwd=str(ROOT))
        
        # 2. Run Caption timing generator
        cmd2 = [py_exe, str(ROOT / "tools" / "update_kokoro_captions.py"), "--project", rel_proj]
        res2 = subprocess.run(cmd2, capture_output=True, text=True, cwd=str(ROOT))

        output = f"{res1.stdout}\n{res2.stdout}"
        if res1.returncode != 0:
            output += f"\nError in gen_voice: {res1.stderr}"
        if res2.returncode != 0:
            output += f"\nError in captions: {res2.stderr}"

        self.send_json({
            "ok": res1.returncode == 0 and res2.returncode == 0,
            "output": output
        })

    def handle_sync_captions(self, body):
        proj_id = body.get("id")
        pdir = self.get_project_dir(proj_id)
        rel_proj = str(pdir.relative_to(ROOT)).replace("\\", "/")
        py_exe = sys.executable

        cmd = [py_exe, str(ROOT / "tools" / "update_kokoro_captions.py"), "--project", rel_proj]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
        self.send_json({
            "ok": res.returncode == 0,
            "output": res.stdout + ("\n" + res.stderr if res.stderr else "")
        })

    def handle_render(self, body):
        proj_id = body.get("id")
        pdir = self.get_project_dir(proj_id)
        beats_file = pdir / "beats.json" if pdir else None

        comp_id = ""
        if beats_file and beats_file.exists():
            with open(beats_file, encoding="utf-8") as f:
                data = json.load(f)
                comp_id = data.get("composition", "")

        # Fallback to match
        if not comp_id:
            m = re.search(r"short-(\d+)", proj_id)
            if m:
                # e.g. Short2Math
                comp_id = f"Short{m.group(1)}"

        remotion_dir = ROOT / "remotion"
        npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"

        # Step 1: gen registry
        subprocess.run([npm_cmd, "run", "gen"], cwd=str(remotion_dir), capture_output=True)

        # Step 2: render-all
        node_cmd = "node"
        render_args = [node_cmd, "scripts/render-all.mjs"]
        if comp_id:
            render_args.append(comp_id)

        res = subprocess.run(render_args, cwd=str(remotion_dir), capture_output=True, text=True)
        self.send_json({
            "ok": res.returncode == 0,
            "output": res.stdout + ("\n" + res.stderr if res.stderr else "")
        })

    def handle_mix_sfx(self, body):
        proj_id = body.get("id")
        pdir = self.get_project_dir(proj_id)
        sfx_plan = pdir / "sfx-plan.json"
        if not sfx_plan.exists():
            self.send_json({"ok": False, "output": f"sfx-plan.json not found in {proj_id}"})
            return

        py_exe = sys.executable
        rel_plan = str(sfx_plan.relative_to(ROOT)).replace("\\", "/")
        cmd = [py_exe, str(ROOT / "tools" / "mix_sfx.py"), rel_plan]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
        self.send_json({
            "ok": res.returncode == 0,
            "output": res.stdout + ("\n" + res.stderr if res.stderr else "")
        })

    def handle_youtube_upload(self, body):
        py_exe = sys.executable
        cmd = [py_exe, str(ROOT / "upload_youtube.py")]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
        self.send_json({
            "ok": res.returncode == 0,
            "output": res.stdout + ("\n" + res.stderr if res.stderr else "")
        })

    def handle_create_short(self, body):
        new_id = body.get("id", "").strip()
        title = body.get("title", "").strip()
        track = body.get("track", "math")

        if not new_id or not title:
            self.send_json({"ok": False, "error": "Missing ID or Title"}, status=400)
            return

        target_dir = ROOT / "shorts" / new_id
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "output").mkdir(exist_ok=True)

        # Scaffolding template beats.json
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

        # Match prompt keywords to proven niche compositions
        proj_id = "short-2-math"
        if any(w in prompt for w in ["reflog", "git", "commit", "branch", "terminal"]):
            proj_id = "short-4-git"
        elif any(w in prompt for w in ["monty", "door", "probab", "paradox"]):
            proj_id = "short-5-prob"
        elif any(w in prompt for w in ["sort", "bubble", "quick", "algo", "array"]):
            proj_id = "short-3-algo"
        elif any(w in prompt for w in ["fee", "retire", "money", "invest", "percent"]):
            proj_id = "short-10-fees"
        elif any(w in prompt for w in ["orbit", "astronaut", "space", "weightless", "fall"]):
            proj_id = "short-12-orbit"
        elif any(w in prompt for w in ["map", "mercator", "greenland", "africa", "geography"]):
            proj_id = "short-11-map"
        elif any(w in prompt for w in ["coffee", "history", "documentary", "vox"]):
            proj_id = "vox-1-coffee"
        elif any(w in prompt for w in ["excel", "flash fill", "sheet"]):
            proj_id = "short-6-sheet"
        elif any(w in prompt for w in ["phish", "paypal", "url", "security"]):
            proj_id = "short-8-phish"
        elif any(w in prompt for w in ["chord", "music", "song", "piano"]):
            proj_id = "short-9-chords"
        elif any(w in prompt for w in ["chess", "checkmate"]):
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

        # 1. Synthesize voice with Kokoro
        cmd_voice = [py_exe, str(ROOT / "tools" / "gen_voice_kokoro.py"), "--project", rel_proj, "--voice", voice, "--speed", str(speed)]
        subprocess.run(cmd_voice, cwd=str(ROOT), capture_output=True)

        # 2. Sync captions
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

        # 4. Find video URL
        output_dir = pdir / "output"
        video_url = None
        if output_dir.exists():
            mp4s = list(output_dir.glob("*-final.mp4")) or list(output_dir.glob("*-sfx.mp4")) or list(output_dir.glob("*.mp4"))
            if mp4s:
                video_url = "/" + str(mp4s[0].relative_to(ROOT)).replace("\\", "/")

        if not video_url:
            remotion_final = ROOT / "shorts" / "short-2-math" / "output" / "short-2-final.mp4"
            if remotion_final.exists():
                video_url = "/" + str(remotion_final.relative_to(ROOT)).replace("\\", "/")

        voice_url = "/" + rel_proj + "/output/kokoro/voice.wav"

        self.send_json({
            "ok": True,
            "id": proj_id,
            "title": title,
            "script": script_text,
            "videoUrl": video_url,
            "voiceUrl": voice_url
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
                # Partial Content (HTTP 206)
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
                # Full Content (HTTP 200)
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
    print("Open your browser and navigate to the link above.")
    print("Press Ctrl+C to stop the server.\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
