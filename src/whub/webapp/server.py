"""FastAPI application factory for the whub web app."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from whub.models import ManifestError
from whub.services.errors import NotFoundError, ServiceError
from whub.webapp.routers.backlog import router as backlog_router
from whub.webapp.routers.inbox import router as inbox_router
from whub.webapp.routers.projects import router as projects_router
from whub.webapp.routers.status import router as status_router
from whub.webapp.routers.todos import router as todos_router


def create_app(dist_dir: Path) -> FastAPI:
    """Create the whub web application serving DIST_DIR."""
    resolved_dist_dir = dist_dir.resolve()
    index_path = resolved_dist_dir / "index.html"
    app = FastAPI()

    @app.exception_handler(NotFoundError)
    def not_found_error_handler(
        request: Request,
        error: NotFoundError,
    ) -> JSONResponse:
        del request
        return JSONResponse(status_code=404, content={"detail": str(error)})

    @app.exception_handler(ServiceError)
    def service_error_handler(
        request: Request,
        error: ServiceError,
    ) -> JSONResponse:
        del request
        return JSONResponse(status_code=400, content={"detail": str(error)})

    @app.exception_handler(ManifestError)
    def manifest_error_handler(
        request: Request,
        error: ManifestError,
    ) -> JSONResponse:
        del request
        return JSONResponse(status_code=500, content={"detail": str(error)})

    app.include_router(todos_router)
    app.include_router(projects_router)
    app.include_router(backlog_router)
    app.include_router(inbox_router)
    app.include_router(status_router)

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
