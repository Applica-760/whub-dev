"""whub app — serve the local web application."""
from __future__ import annotations

import webbrowser

import click
import uvicorn

from whub.paths import app_dist_path
from whub.webapp.server import create_app


@click.command()
@click.option("--port", type=int, default=8710, show_default=True)
@click.option("--no-open", is_flag=True, help="Do not open a browser.")
def app(port: int, no_open: bool) -> None:
    """Serve the whub web app on localhost."""
    dist_dir = app_dist_path()
    if not (dist_dir / "index.html").is_file():
        raise click.ClickException(
            "web app is not built; run `cd app && npm install && npm run build`"
        )

    url = f"http://127.0.0.1:{port}"
    if not no_open:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    uvicorn.run(create_app(dist_dir), host="127.0.0.1", port=port)
