"""Desktop Webview Application Runner for Generator Laporan."""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path

import webview

from .. import database, logging_setup, paths
from .api_bridge import ApiBridge

WINDOW_TITLE = "Generator Laporan Akademik"


def clamp_window_to_workarea() -> None:
    """Pastikan jendela berada DI DALAM area kerja yang terlihat (tidak tertutup taskbar).

    Ukuran bawaan 1320x850 bisa melebihi ruang layar pada laptop 1366x768 atau
    saat skala tampilan Windows besar, sehingga sisi bawah jendela (tombol
    ekspor, panel inspektur) berada di belakang taskbar. Fungsi ini dipanggil
    setelah GUI hidup: cari HWND jendela, bandingkan dengan area kerja monitor
    (semua dalam piksel fisik, jadi kebal kebingungan DPI), lalu kecilkan dan
    pusatkan bila perlu.
    """
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", wintypes.LONG), ("top", wintypes.LONG),
                ("right", wintypes.LONG), ("bottom", wintypes.LONG),
            ]

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD), ("rcMonitor", RECT),
                ("rcWork", RECT), ("dwFlags", wintypes.DWORD),
            ]

        hwnd = 0
        for _ in range(50):  # tunggu jendela benar-benar diciptakan (maks 10 s)
            hwnd = user32.FindWindowW(None, WINDOW_TITLE)
            if hwnd:
                break
            time.sleep(0.2)
        if not hwnd:
            return
        if user32.IsZoomed(hwnd):  # jendela maksimal sudah patuh area kerja
            return

        monitor = user32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            return
        rect = RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return

        work = info.rcWork
        cur_w = rect.right - rect.left
        cur_h = rect.bottom - rect.top
        new_w = min(cur_w, work.right - work.left)
        new_h = min(cur_h, work.bottom - work.top)
        new_left = rect.left
        new_top = rect.top
        if new_w != cur_w:
            new_left = work.left + ((work.right - work.left) - new_w) // 2
        if new_h != cur_h:
            new_top = work.top + ((work.bottom - work.top) - new_h) // 2
        new_left = max(work.left, min(new_left, work.right - new_w))
        new_top = max(work.top, min(new_top, work.bottom - new_h))

        if (new_w, new_h, new_left, new_top) != (cur_w, cur_h, rect.left, rect.top):
            user32.SetWindowPos(hwnd, 0, new_left, new_top, new_w, new_h, 0x0040)  # SWP_NOZORDER
    except Exception:
        # Penjepitan jendela bersifat kosmetik; jangan ganggu aplikasi bila gagal.
        pass


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
        title=WINDOW_TITLE,
        url=url,
        js_api=bridge,
        width=1320,
        height=850,
        min_size=(960, 640),
        text_select=True,
    )
    bridge.set_window(window)

    try:
        webview.start(func=clamp_window_to_workarea, debug=dev_mode)
    finally:
        db.close()
        log.info("Webview app closed cleanly.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
