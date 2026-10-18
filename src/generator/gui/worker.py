"""Worker latar: operasi lama berjalan di thread, UI hanya disentuh lewat `after` (temuan 6).

Aturan: OCR, panggilan AI per batch, ambil web, dan render WAJIB lewat
`run_in_thread`; callback `on_success`/`on_error` dijalankan di thread utama
Tkinter, bukan di thread pekerja.

GC sengaja dipatikan selama thread pekerja hidup dan diaktifkan kembali di
poll (thread utama): pass GC di thread pekerja bisa mengumpulkan `Variable`
milik jendela yang sudah ditutup, dan `Variable.__del__` memanggil Tcl dari
thread asing pada interpreter mati sehingga render bisa macet selamanya
(terbukti dengan `faulthandler` saat ekspor DOCX, Task 17c).
"""

from __future__ import annotations

import gc
import queue
import threading
from typing import Callable

_POLL_MS = 50

_gc_lock = threading.Lock()
_gc_depth = 0


def _gc_pause() -> None:
    """Larang GC proses; dipanggil sebelum thread pekerja mulai bekerja."""
    global _gc_depth
    with _gc_lock:
        if _gc_depth == 0:
            gc.disable()
        _gc_depth += 1


def _gc_resume() -> None:
    """Aktifkan kembali GC; harus dipanggil dari thread utama (poll)."""
    global _gc_depth
    with _gc_lock:
        _gc_depth = max(0, _gc_depth - 1)
        if _gc_depth == 0:
            gc.enable()


def _drain(q: queue.Queue, on_success, on_error) -> bool:
    """Ambil satu hasil dari antrean; True bila ada, False bila kosong."""
    try:
        kind, payload = q.get_nowait()
    except queue.Empty:
        return False
    if kind == "ok":
        if on_success is not None:
            on_success(payload)
    else:
        if on_error is not None:
            on_error(payload)
    return True


def run_in_thread(widget, work: Callable, on_success=None, on_error=None) -> None:
    """Jalankan `work()` di thread daemon; hasil diteruskan lewat `widget.after`.

    Widget sama sekali tidak disentuh dari dalam thread pekerja.
    """
    results: queue.Queue = queue.Queue()

    def target() -> None:
        _gc_pause()
        try:
            results.put(("ok", work()))
        except Exception as error:  # semua kegagalan diteruskan ke UI
            results.put(("err", error))

    threading.Thread(target=target, daemon=True, name="generator-worker").start()

    def poll() -> None:
        if _drain(results, on_success, on_error):
            _gc_resume()  # aman: berjalan di thread utama
            return
        widget.after(_POLL_MS, poll)

    widget.after(0, poll)
