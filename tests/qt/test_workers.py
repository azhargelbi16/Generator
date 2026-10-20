"""Tes worker thread Qt: hasil, error, dan pembatalan (addendum A.4)."""

import threading
import time

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtTest import QTest


def _until_done(worker, timeout_ms=5000):
    """Tunggu sinyal finished worker; loop event berjalan di thread tes."""
    loop = QEventLoop()
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    worker.finished.connect(loop.quit)
    timer.start(timeout_ms)
    loop.exec()
    timer.stop()


def test_work_murni_memancarkan_result(qapp):
    from generator.qt.workers import run_in_thread

    got = {}
    thread, worker = run_in_thread(None, lambda: 42)
    worker.result.connect(lambda value: got.setdefault("value", value))
    _until_done(worker)
    assert got["value"] == 42
    thread.wait(2000)
    assert not thread.isRunning()


def test_work_gagal_memancarkan_error(qapp):
    from generator.qt.workers import run_in_thread

    got = {}

    def boom():
        raise ValueError("meledak")

    thread, worker = run_in_thread(None, boom)
    worker.error.connect(lambda message: got.setdefault("message", message))
    _until_done(worker)
    assert "meledak" in got["message"]
    thread.wait(2000)


def test_request_cancel_menghentikan_loop_kerja(qapp):
    from generator.qt.workers import run_in_thread

    state = {"ran": 0, "cancelled": False, "result": None}
    cancel = threading.Event()

    def loop_work():
        while not cancel.is_set():
            state["ran"] += 1
            time.sleep(0.005)
        return "selesai"

    thread, worker = run_in_thread(None, loop_work, cancel_event=cancel)
    worker.cancelled.connect(lambda: state.__setitem__("cancelled", True))
    worker.result.connect(lambda value: state.__setitem__("result", value))
    QTest.qWait(60)  # biarkan loop berjalan dulu
    worker.request_cancel()
    _until_done(worker)
    assert state["ran"] > 0
    assert state["cancelled"] is True
    assert state["result"] is None
    thread.wait(2000)
