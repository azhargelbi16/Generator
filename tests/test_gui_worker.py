import queue
import threading
import time
from generator.gui import worker


class FakeWidget:
    def __init__(self):
        self.after_ms = []

    def after(self, ms, fn):
        self.after_ms.append(ms)
        time.sleep(0.001)  # beri kesempatan thread pekerja menyelesaikan hasil
        fn()


def test_drain_calls_success():
    q = queue.Queue(); q.put(("ok", 7)); got = []
    assert worker._drain(q, got.append, None) is True
    assert got == [7]


def test_drain_returns_false_when_empty():
    assert worker._drain(queue.Queue(), lambda v: None, None) is False


def test_run_in_thread_delivers_result_via_after():
    w = FakeWidget(); done = threading.Event(); box = []
    def on_success(v): box.append(v); done.set()
    worker.run_in_thread(w, lambda: 42, on_success=on_success)
    assert done.wait(2.0) and box == [42]
    assert w.after_ms  # pembaruan UI lewat after, bukan thread pekerja
