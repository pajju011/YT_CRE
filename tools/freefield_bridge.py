#!/usr/bin/env python3
"""
freefield_bridge.py — Bridge interface between VideoGenerator Studio and Freefield (120+ Apps).

Reads app manifests from freefield/apps/*/app.json, parses workflow graphs,
monitors the Freefield server process on port 3005, and provides discovery.
"""

import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
FREEFIELD_DIR = ROOT / "freefield"
APPS_DIR = FREEFIELD_DIR / "apps"
PORT = 3005
FREEFIELD_URL = f"http://127.0.0.1:{PORT}"
FREEFIELD_PROCESS = None


def is_freefield_running():
    """Checks if the Freefield server is responding on port 3005."""
    try:
        req = urllib.request.Request(f"{FREEFIELD_URL}/api/apps", headers={"Host": f"127.0.0.1:{PORT}"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False


def start_freefield_server():
    """Starts the Freefield Node.js server as a background process if not already running."""
    global FREEFIELD_PROCESS
    if is_freefield_running():
        return {"ok": True, "url": FREEFIELD_URL, "status": "already_running"}

    cmd = [
        "node",
        "--env-file-if-exists=.env",
        "--experimental-strip-types",
        "--disable-warning=ExperimentalWarning",
        "server/server.ts"
    ]
    try:
        FREEFIELD_PROCESS = subprocess.Popen(
            cmd,
            cwd=str(FREEFIELD_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
        )
        return {"ok": True, "url": FREEFIELD_URL, "status": "started"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_freefield_catalog():
    """Reads all app manifests from freefield/apps/*/app.json."""
    if not APPS_DIR.exists():
        return []

    catalog = []
    for app_dir in APPS_DIR.iterdir():
        if not app_dir.is_dir():
            continue
        manifest_file = app_dir / "app.json"
        if not manifest_file.exists():
            continue
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                catalog.append({
                    "id": data.get("id", app_dir.name),
                    "title": data.get("title", app_dir.name.replace("-", " ").title()),
                    "category": data.get("category", "video"),
                    "pack": data.get("pack", "core"),
                    "status": data.get("status", "ready"),
                    "desc": data.get("desc", ""),
                    "models": [m.get("file", "") for m in data.get("models", [])]
                })
        except Exception:
            continue

    catalog.sort(key=lambda x: (x["category"], x["title"]))
    return catalog


def get_app_workflow(app_id):
    """Returns the raw ComfyUI workflow JSON for a given app ID."""
    wf_path = APPS_DIR / app_id / "workflow.json"
    if not wf_path.exists():
        return None
    try:
        with open(wf_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


if __name__ == "__main__":
    apps = get_freefield_catalog()
    print(f"Discovered {len(apps)} Freefield Apps:")
    for a in apps[:10]:
        print(f"  • [{a['category']}] {a['id']}: {a['title']} ({len(a['models'])} models)")
    print(f"Server running: {is_freefield_running()}")
