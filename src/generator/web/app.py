"""Desktop Webview Application Runner for Generator Laporan."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import webview

from .. import database, logging_setup, paths
from .api_bridge import ApiBridge


def main() -> int:
    try:
        paths.ensure_dirs()
    except Exception as e:
        print(f"Error initializing paths: {e}", file=sys.stderr)
        return 1

    logging_setup.setup_logging(paths.LOG_PATH)
    log = logging.getLogger("generator.web.app")
    log.info("Starting Generator Laporan Webview Desktop...")

    db = database.Database(paths.DB_PATH)
    db.init_schema()

    bridge = ApiBridge(db, paths.CONFIG_PATH)

    # Determine URL: check if built dist exists, otherwise fall back to dev server or local file
    dist_index = paths.PROJECT_ROOT / "frontend" / "dist" / "index.html"
    dev_mode = os.environ.get("GENERATOR_DEV", "").lower() in ("1", "true", "yes")

    if dev_mode:
        url = "http://localhost:5173"
        log.info(f"Dev mode active. Loading {url}")
    elif dist_index.is_file():
        url = str(dist_index.resolve())
        log.info(f"Loading built frontend from {url}")
    else:
        url = "http://localhost:5173"
        log.warning(f"{dist_index} not found. Attempting dev server at {url}")

    window = webview.create_window(
        title="Generator Laporan Akademik",
        url=url,
        js_api=bridge,
        width=1320,
        height=850,
        min_size=(960, 640),
        text_select=True,
    )
    bridge.set_window(window)

    try:
        webview.start(debug=dev_mode)
    finally:
        db.close()
        log.info("Webview app closed cleanly.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
