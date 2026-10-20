"""Worker thread Qt: satu pola untuk semua kerja berat di background (addendum A.4).

Pengganti gui/worker.run_in_thread: kerja berjalan di QThread, hasil kembali
lewat sinyal; UI hanya boleh disentuh dari thread utama melalui koneksi sinyal.
Pembatalan via threading.Event yang dilewatkan ke engine.
"""

from __future__ import annotations

import threading
from typing import Callable

from PySide6.QtCore import QObject, QThread, Signal


class Worker(QObject):
    result = Signal(object)
    error = Signal(str)
    progress = Signal(dict)
    cancelled = Signal()
    finished = Signal()

    def __init__(self, work: Callable, cancel_event: threading.Event | None = None):
        super().__init__()
        self._work = work
        self._cancel_event = cancel_event or threading.Event()

    @property
    def cancel_event(self) -> threading.Event:
        return self._cancel_event

    def request_cancel(self) -> None:
        self._cancel_event.set()

    def run(self) -> None:
        try:
            result = self._work()
        except Exception as exc:  # UI menerima pesan, thread tetap selesai bersih
            self.error.emit(str(exc))
        else:
            if self._cancel_event.is_set():
                self.cancelled.emit()
            else:
                self.result.emit(result)
        finally:
            self.finished.emit()


_LINGERING: list[QThread] = []


def linger(thread: QThread) -> None:
    """Lepas thread yang belum selesai dari parent agar tidak dimusnahkan saat tutup.

    Dipakai hanya saat shutdown: QThread yang dihancurkan sementara masih berjalan
    membuat Qt abort. Proses yang masih memegang thread ini keluar lewat os._exit
    (lihat app.main) supaya destructor QThread tidak sempat jalan.
    """
    if thread in _LINGERING:
        return
    thread.setParent(None)
    _LINGERING.append(thread)
    thread.finished.connect(lambda: _LINGERING.remove(thread) if thread in _LINGERING else None)


def has_lingering() -> bool:
    return any(thread.isRunning() for thread in _LINGERING)


def run_in_thread(
    parent: QObject | None,
    work: Callable,
    cancel_event: threading.Event | None = None,
) -> tuple[QThread, Worker]:
    """Jalankan `work` di QThread; kembalikan (thread, worker) yang bisa dibatalkan."""
    event = cancel_event or threading.Event()
    thread = QThread(parent)
    worker = Worker(work, event)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    thread.finished.connect(worker.deleteLater)
    thread.start()
    return thread, worker
