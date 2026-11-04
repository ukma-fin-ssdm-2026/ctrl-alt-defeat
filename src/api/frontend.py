"""
Serves the built React app (frontend/dist) from FastAPI, so the site and the API share one origin
in a container deployment (session cookie works, no CORS). Enabled by FRONTEND_DIST_DIR.
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Paths that always belong to the backend and must never fall back to index.html
BACKEND_PREFIXES = ("api/", "health", "api-docs", "redoc", "openapi.json", "docs/")


def mount_frontend(app: FastAPI, dist_dir: str) -> bool:
    dist = Path(dist_dir).resolve()
    index_file = dist / "index.html"
    if not index_file.is_file():
        return False

    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="frontend-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        if full_path.startswith(BACKEND_PREFIXES):
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = (dist / full_path).resolve()
        # Only real files inside dist (logo, favicon...); everything else is a client-side route
        if full_path and candidate.is_file() and dist in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(index_file)

    return True
