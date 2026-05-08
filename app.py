"""Flask web app:
- serves the cron-generated dashboard snapshots (read-only)
- renders /favorites room (mutable)
- exposes JSON APIs for star/unstar + chat
"""
import json
import os
import threading
from datetime import datetime
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request, send_from_directory

DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data"))
WEB_DIR = Path(os.getenv("WEB_DIR", str(DATA_DIR / "web")))
PORT = int(os.getenv("PORT") or "3000")
PARTICIPANTS = [n.strip() for n in os.getenv("PARTICIPANTS", "").split(",") if n.strip()]

DATA_DIR.mkdir(parents=True, exist_ok=True)
WEB_DIR.mkdir(parents=True, exist_ok=True)

FAV_FILE = DATA_DIR / "favorites.json"
CHAT_FILE = DATA_DIR / "chat.json"

_lock = threading.Lock()
app = Flask(__name__)


def _load(path: Path, default):
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save(path: Path, data) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def _favorites():
    return _load(FAV_FILE, {"items": {}})


def _chat():
    return _load(CHAT_FILE, {"messages": []})


# ── Static (cron-generated) dashboard ─────────────────────────────────────

@app.route("/")
def index():
    f = WEB_DIR / "index.html"
    if not f.exists():
        return (
            "<h1>Dashboard not generated yet</h1>"
            "<p>The cron job hasn't run. Trigger the Coolify Scheduled Task once.</p>",
            404,
        )
    return send_from_directory(WEB_DIR, "index.html")


@app.route("/<path:name>.html")
def snapshot(name):
    fname = f"{name}.html"
    if not (WEB_DIR / fname).exists():
        abort(404)
    return send_from_directory(WEB_DIR, fname)


# ── Favorites room ────────────────────────────────────────────────────────

@app.route("/favorites")
def favorites_page():
    favs = _favorites()
    items = sorted(
        favs["items"].values(),
        key=lambda a: a.get("added_at", ""),
        reverse=True,
    )
    return render_template(
        "favorites.html",
        favorites=items,
        participants=PARTICIPANTS or ["Anonymous"],
    )


# ── Favorites API ─────────────────────────────────────────────────────────

@app.route("/api/favorites/ids")
def api_fav_ids():
    return jsonify(list(_favorites()["items"].keys()))


@app.route("/api/favorites", methods=["GET"])
def api_fav_list():
    return jsonify(list(_favorites()["items"].values()))


@app.route("/api/favorites/<apt_id>", methods=["POST"])
def api_fav_add(apt_id):
    body = request.get_json(force=True, silent=True) or {}
    body["id"] = apt_id
    body["added_at"] = datetime.now().astimezone().isoformat()
    with _lock:
        favs = _favorites()
        favs["items"][apt_id] = body
        _save(FAV_FILE, favs)
    return jsonify({"ok": True, "count": len(favs["items"])})


@app.route("/api/favorites/<apt_id>", methods=["DELETE"])
def api_fav_remove(apt_id):
    with _lock:
        favs = _favorites()
        favs["items"].pop(apt_id, None)
        _save(FAV_FILE, favs)
    return jsonify({"ok": True, "count": len(favs["items"])})


# ── Chat API ──────────────────────────────────────────────────────────────

@app.route("/api/chat", methods=["GET"])
def api_chat_list():
    since = int(request.args.get("since", "0") or "0")
    msgs = _chat()["messages"]
    if since:
        msgs = [m for m in msgs if m["id"] > since]
    return jsonify(msgs)


@app.route("/api/chat", methods=["POST"])
def api_chat_post():
    body = request.get_json(force=True, silent=True) or {}
    user = (body.get("user") or "Anonymous").strip()[:50]
    text = (body.get("text") or "").strip()[:2000]
    if not text:
        return jsonify({"error": "empty"}), 400
    with _lock:
        chat = _chat()
        next_id = max((m["id"] for m in chat["messages"]), default=0) + 1
        msg = {
            "id": next_id,
            "user": user,
            "text": text,
            "ts": datetime.now().astimezone().isoformat(),
        }
        chat["messages"].append(msg)
        _save(CHAT_FILE, chat)
    return jsonify(msg)


if __name__ == "__main__":
    print(f"[app] DATA_DIR={DATA_DIR}  WEB_DIR={WEB_DIR}  PORT={PORT}", flush=True)
    print(f"[app] Participants: {PARTICIPANTS or '(none — defaults to Anonymous)'}", flush=True)
    app.run(host="0.0.0.0", port=PORT, debug=False)
