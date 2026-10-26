import os
import re
import shutil
import tempfile
import time
from urllib.parse import urlparse

import yt_dlp
from flask import Flask, jsonify, render_template, request, send_file, after_this_request

app = Flask(__name__)

ALLOWED_HOSTS = ("tiktok.com",)   # also covers vm.tiktok.com, vt.tiktok.com
MAX_REQUESTS_PER_MINUTE = 6       # per visitor, keeps free hosting from being overloaded
MAX_FILESIZE = 100 * 1024 * 1024  # 100 MB
_hits = {}


def is_tiktok_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    return any(host == h or host.endswith("." + h) for h in ALLOWED_HOSTS)


def too_many_requests() -> bool:
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()
    now = time.time()
    recent = [t for t in _hits.get(ip, []) if now - t < 60]
    recent.append(now)
    _hits[ip] = recent
    if len(_hits) > 5000:  # stop the dict growing forever
        _hits.clear()
    return len(recent) > MAX_REQUESTS_PER_MINUTE


def ydl_options(**extra):
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": 15,
        "format": "best[ext=mp4]/best",
    }
    opts.update(extra)
    return opts


def safe_name(title: str) -> str:
    cleaned = re.sub(r"[^\w\- ]+", "", title or "", flags=re.UNICODE).strip()
    return (cleaned[:60] or "tiktok-video")


@app.get("/")
def home():
    return render_template("index.html")


@app.post("/api/info")
def info():
    url = ((request.get_json(silent=True) or {}).get("url") or "").strip()
    if not is_tiktok_url(url):
        return jsonify(error="Paste a link that starts with https://www.tiktok.com or https://vm.tiktok.com."), 400
    if too_many_requests():
        return jsonify(error="Too many requests. Wait a minute and try again."), 429
    try:
        with yt_dlp.YoutubeDL(ydl_options()) as ydl:
            data = ydl.extract_info(url, download=False)
    except Exception:
        return jsonify(error="Couldn't read this video. It may be private, deleted, or TikTok blocked the request. Try again later."), 502
    return jsonify(
        title=data.get("title") or "TikTok video",
        uploader=data.get("uploader") or "",
        thumbnail=data.get("thumbnail") or "",
        duration=data.get("duration") or 0,
    )


@app.get("/api/download")
def download():
    url = (request.args.get("url") or "").strip()
    if not is_tiktok_url(url):
        return jsonify(error="Invalid TikTok link."), 400
    if too_many_requests():
        return jsonify(error="Too many requests. Wait a minute and try again."), 429

    workdir = tempfile.mkdtemp(prefix="ttdl_")

    @after_this_request
    def cleanup(response):
        shutil.rmtree(workdir, ignore_errors=True)
        return response

    try:
        opts = ydl_options(outtmpl=os.path.join(workdir, "video.%(ext)s"), max_filesize=MAX_FILESIZE)
        with yt_dlp.YoutubeDL(opts) as ydl:
            data = ydl.extract_info(url, download=True)
        files = os.listdir(workdir)
        if not files:
            raise RuntimeError("no file")
        path = os.path.join(workdir, files[0])
        ext = os.path.splitext(path)[1] or ".mp4"
        return send_file(path, as_attachment=True, download_name=safe_name(data.get("title")) + ext)
    except Exception:
        shutil.rmtree(workdir, ignore_errors=True)
        return jsonify(error="Download failed. The video may be private or too large."), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
