#!/usr/bin/env python3
"""yt-transcribe-web: public web front for the private yt-transcribe GPU service.

Thin authenticated gateway: serves a single-page UI and proxies job calls to the
upstream yt-transcribe API (niko GPU box) with the Bearer token held server-side.
Env: YT_API_URL, YT_API_TOKEN, WEB_USER, WEB_PASS.
"""
import os
import secrets
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

APP_DIR = Path(__file__).resolve().parent

UPSTREAM = os.environ.get("YT_API_URL", "https://yt-api.airobotika.com").rstrip("/")
UPSTREAM_TOKEN = os.environ.get("YT_API_TOKEN", "")
WEB_USER = os.environ.get("WEB_USER", "airobotika")
WEB_PASS = os.environ.get("WEB_PASS", "")

if not WEB_PASS:
    raise RuntimeError("WEB_PASS env must be set")
if not UPSTREAM_TOKEN:
    raise RuntimeError("YT_API_TOKEN env must be set")

app = FastAPI(title="yt-transcribe-web", version="1.0")
client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0))


# ------------------------------------------------------------------ auth gate
def require_auth(request: Request):
    expected = f"{WEB_USER}:{WEB_PASS}".encode()
    header = request.headers.get("authorization", "")
    supplied = ""
    if header.lower().startswith("basic "):
        import base64
        try:
            supplied = base64.b64decode(header[6:]).decode()
        except Exception:
            supplied = ""
    if not secrets.compare_digest(supplied.encode(), expected):
        raise HTTPException(
            401, "auth required",
            headers={"WWW-Authenticate": 'Basic realm="yt-transcribe", charset="UTF-8"'},
        )


async def upstream_request(method: str, path: str, **kw):
    headers = {"Authorization": f"Bearer {UPSTREAM_TOKEN}"}
    try:
        r = await client.request(method, f"{UPSTREAM}{path}", headers=headers, **kw)
    except httpx.HTTPError as e:
        raise HTTPException(502, f"upstream unreachable: {e.__class__.__name__}")
    return r


# ------------------------------------------------------------------ pages
@app.get("/", include_in_schema=False)
async def index(_=Depends(require_auth)):
    return FileResponse(APP_DIR / "static" / "index.html")


@app.get("/healthz")
async def healthz():
    return {"ok": True}


# ------------------------------------------------------------------ api proxy
@app.post("/api/transcribe", include_in_schema=False)
async def transcribe(request: Request, _=Depends(require_auth)):
    body = await request.json()
    url = (body.get("url") or "").strip()
    if not url:
        raise HTTPException(422, "url is required")
    payload = {"url": url}
    if body.get("language"):
        payload["language"] = body["language"]
    r = await upstream_request("POST", "/transcribe", json=payload)
    return JSONResponse(r.json(), status_code=r.status_code)


@app.get("/api/jobs/{job_id}", include_in_schema=False)
async def job_status(job_id: str, _=Depends(require_auth)):
    r = await upstream_request("GET", f"/jobs/{job_id}")
    return JSONResponse(r.json(), status_code=r.status_code)


@app.get("/api/jobs/{job_id}/{fmt}", include_in_schema=False)
async def job_output(job_id: str, fmt: str, download: int = 0, _=Depends(require_auth)):
    if fmt not in ("text", "srt", "vtt", "json"):
        raise HTTPException(404, "unknown format")
    r = await upstream_request("GET", f"/jobs/{job_id}/{fmt}")
    if r.status_code != 200:
        raise HTTPException(r.status_code, r.text[:300])
    media = {"text": "text/plain; charset=utf-8",
             "srt": "application/x-subrip",
             "vtt": "text/vtt",
             "json": "application/json"}[fmt]
    disp = "attachment" if download else "inline"
    return StreamingResponse(
        iter([r.content]), media_type=media,
        headers={"Content-Disposition": f'{disp}; filename="transcript.{fmt}"'},
    )
