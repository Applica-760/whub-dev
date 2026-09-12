"""FastAPI application factory for the whub web app."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from whub.core.context import PathError
from whub.models import ManifestError
from whub.services.errors import NotFoundError, ServiceError
from whub.webapp.routers.backlog import router as backlog_router
from whub.webapp.routers.agent_attention import router as agent_attention_router
from whub.webapp.routers.agent_sessions import router as agent_sessions_router
from whub.webapp.routers.daily import router as daily_router
from whub.webapp.routers.hub_explorer import router as hub_explorer_router
from whub.webapp.routers.inbox import router as inbox_router
from whub.webapp.routers.issues import router as issues_router
from whub.webapp.routers.operator_terminal import (
    operator_terminal_socket,
    router as operator_terminal_router,
)
from whub.webapp.routers.projects import router as projects_router
from whub.webapp.routers.status import router as status_router
from whub.webapp.routers.tasks import router as tasks_router
from whub.webapp.routers.terminal import terminal
from whub.webapp.routers.todos import router as todos_router
from whub.webapp.routers.vault import router as vault_router


def create_api_app() -> FastAPI:
    """Create the API application used by the development server."""
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

    @app.exception_handler(PathError)
    def path_error_handler(
        request: Request,
        error: PathError,
    ) -> JSONResponse:
        del request
        return JSONResponse(status_code=500, content={"detail": str(error)})

    app.include_router(todos_router)
    app.include_router(projects_router)
    app.include_router(backlog_router)
    app.include_router(agent_attention_router)
    app.include_router(agent_sessions_router)
    app.include_router(daily_router)
    app.include_router(inbox_router)
    app.include_router(issues_router)
    app.include_router(status_router)
    app.include_router(tasks_router)
    app.add_api_websocket_route("/api/terminals/{project}/{issue_number}", terminal)
    app.include_router(operator_terminal_router)
    app.add_api_websocket_route(
        "/api/operator-terminals/{operator_id}", operator_terminal_socket
    )
    app.include_router(vault_router)
    app.include_router(hub_explorer_router)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


def create_app(dist_dir: Path) -> FastAPI:
    """Create the whub web application serving DIST_DIR."""
    resolved_dist_dir = dist_dir.resolve()
    index_path = resolved_dist_dir / "index.html"
    app = create_api_app()

    @app.get("/{path:path}", include_in_schema=False)
    def serve_spa(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404)

        requested_path = (resolved_dist_dir / path).resolve()
        if (
            requested_path.is_relative_to(resolved_dist_dir)
            and requested_path.is_file()
        ):
            return FileResponse(requested_path)
        return FileResponse(index_path)

    return app
