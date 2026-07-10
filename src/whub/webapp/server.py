"""FastAPI application factory for the whub web app."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse


def create_app(dist_dir: Path) -> FastAPI:
    """Create the whub web application serving DIST_DIR."""
    resolved_dist_dir = dist_dir.resolve()
    index_path = resolved_dist_dir / "index.html"
    app = FastAPI()

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/{path:path}", include_in_schema=False)
    def serve_spa(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404)

        requested_path = (resolved_dist_dir / path).resolve()
        if requested_path.is_relative_to(resolved_dist_dir) and requested_path.is_file():
            return FileResponse(requested_path)
        return FileResponse(index_path)

    return app
