"""Export the whub web API schema without starting a server."""

from __future__ import annotations

import json
from typing import Any

from whub.core.paths import app_dist_path
from whub.webapp.server import create_app


def openapi_schema() -> dict[str, Any]:
    """Return the current web API OpenAPI schema."""
    return create_app(app_dist_path()).openapi()


def main() -> None:
    """Write the OpenAPI schema to standard output."""
    print(json.dumps(openapi_schema(), indent=2))


if __name__ == "__main__":
    main()
