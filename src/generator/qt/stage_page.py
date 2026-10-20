"""Panggung Penuh Qt: dokumen menulis dirinya saat generate (addendum D.2).

Worker memanggil `content.generate_sections(..., progress=_StageProgress,
cancel=event)`. `_StageProgress` berjalan di thread worker dan hanya memancarkan
sinyal — widget hanya disentuh dari thread UI. Reveal kalimat dijeda lewat
QTimer singkat (maks ~2 kalimat per 30ms) supaya tidak menahan event loop;
perilaku engine tidak berubah, ini presentasi.
"""

from __future__ import annotations

import threading
import time

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .. import config, paths
from ..ai import content
from ..ai.client import AIClient
from ..verification import STATUS_NON_FACTUAL, STATUS_UNVERIFIED, STATUS_VERIFIED
from .workers import run_in_thread

_STATUS_LABELS = {
    STATUS_VERIFIED: "terverifikasi",
    STATUS_UNVERIFIED: "belum terverifikasi",
    STATUS_NON_FACTUAL: "bukan klaim faktual",
}

_REVEAL_INTERVAL_MS = 30
_REVEAL_PER_TICK = 2

_KITCHEN_QSS = """
QListWidget {
    background-color: #1f2430;
    color: #d7dce5;
    border: none;
    font-family: "Consolas", monospace;
}
"""


class _StageProgress(content.GenerationProgress):
    """Terjemahkan callback engine (thread worker) menjadi sinyal UI."""

    def __init__(self, page: "StagePage"):
        self._page = page
        self._total = 0

    def batch_started(self, n: int, total_batches: int) -> None:
        self.batch_count = n
        self._total = total_batches
        self._page.batchProgress.emit(n, total_batches, self.sentence_hint, self.sentence_hint)
        self._page.narrate.emit(f"Menulis bab {n}...")

    def sentence_born(self, sentence, status: str) -> None:
        self.sentence_hint += 1
        self._page.sentenceArrived.emit(sentence.text, status)
        self._page.batchProgress.emit(
            self.batch_count, self._total, self.sentence_hint, self.sentence_hint
        )
        self._page.narrate.emit("Memverifikasi kutipan")

    def finished(self, cancelled: bool) -> None:
        self._page.narrate.emit("Generate dibatalkan." if cancelled else "Generate selesai.")


class StagePage(QWidget):
    """Halaman panggung: dokumen, progres per bab, dapur AI, tombol Batal."""

    sentenceArrived = Signal(str, str)  # teks, status
    narrate = Signal(str)
    batchProgress = Signal(int, int, int, int)  # bab ke-, dari, kalimat, total_hint
    finished = Signal(bool)  # True = dibatalkan

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._client_factory = lambda: AIClient(config.load_config(paths.CONFIG_PATH))
        self._thread = None
        self._worker = None
        self._cancel_event: threading.Event | None = None
        self.result_sections: list | None = None
        self._queue: list[tuple[str, str]] = []
        self._started_at = 0.0
        self._done_generating = True

        layout = QHBoxLayout(self)

        left = QVBoxLayout()
        layout.addLayout(left, stretch=3)
        self._batch_label = QLabel("-")
        left.addWidget(self._batch_label)
        self._progress_bar = QProgressBar()
        left.addWidget(self._progress_bar)
        self._eta_label = QLabel("-")
        left.addWidget(self._eta_label)
        self._document = QTextEdit()
        self._document.setReadOnly(True)
        left.addWidget(self._document, stretch=1)
        self._cancel_button = QPushButton("Batal")
        self._cancel_button.setEnabled(False)
        self._cancel_button.clicked.connect(self.cancel)
        left.addWidget(self._cancel_button)

        right = QVBoxLayout()
        layout.addLayout(right, stretch=1)
        right.addWidget(QLabel("Dapur AI"))
        self._kitchen = QListWidget()
        self._kitchen.setStyleSheet(_KITCHEN_QSS)
        right.addWidget(self._kitchen)

        self._reveal_timer = QTimer(self)
        self._reveal_timer.setInterval(_REVEAL_INTERVAL_MS)
        self._reveal_timer.timeout.connect(self._reveal_some)

        self.sentenceArrived.connect(self._enqueue_sentence)
        self.narrate.connect(self._append_kitchen)
        self.batchProgress.connect(self._on_batch_progress)

    # ------------------------------------------------------------------ API

    def start_generate(self, state, max_prompt_chars: int = 12000) -> None:
        """Mulai generate dari state controller (duck-typing `generate_plan()`)."""
        topic, outline, sources, texts = state.generate_plan()
        self._reset()
        self.narrate.emit("Membaca sumber...")
        self._started_at = time.monotonic()
        self._done_generating = False
        cancel = threading.Event()
        self._cancel_event = cancel
        progress = _StageProgress(self)

        def work():
            sections = content.generate_sections(
                topic, outline, sources, texts,
                self._client_factory(),
                max_prompt_chars=max_prompt_chars,
                progress=progress,
                cancel=cancel,
            )
            self.result_sections = sections
            return sections

        self._thread, self._worker = run_in_thread(self, work, cancel_event=cancel)
        self._worker.result.connect(lambda _sections: self._wrap_up(False))
        self._worker.cancelled.connect(lambda: self._wrap_up(True))
        self._worker.error.connect(self._on_error)
        self._cancel_button.setEnabled(True)

    def cancel(self) -> None:
        """Minta engine berhenti; hasil parsial tetap tampil."""
        if self._worker is not None:
            self._worker.request_cancel()
        self._cancel_button.setEnabled(False)

    # ------------------------------------------------------------ internal

    def _reset(self) -> None:
        self._document.clear()
        self._kitchen.clear()
        self._queue.clear()
        self._batch_label.setText("-")
        self._progress_bar.setRange(0, 1)
        self._progress_bar.setValue(0)
        self._eta_label.setText("-")
        self.result_sections = None
        self._reveal_timer.stop()

    def _enqueue_sentence(self, text: str, status: str) -> None:
        self._queue.append((text, status))
        if not self._reveal_timer.isActive():
            self._reveal_timer.start()

    def _reveal_some(self) -> None:
        for _ in range(min(_REVEAL_PER_TICK, len(self._queue))):
            text, status = self._queue.pop(0)
            self._append_sentence(text, status)
        if not self._queue and self._done_generating:
            self._reveal_timer.stop()

    def _flush_queue(self) -> None:
        while self._queue:
            text, status = self._queue.pop(0)
            self._append_sentence(text, status)
        self._reveal_timer.stop()

    def _append_sentence(self, text: str, status: str) -> None:
        label = _STATUS_LABELS.get(status, status)
        self._document.append(f"{text} [{label}]")

    def _append_kitchen(self, message: str) -> None:
        last = self._kitchen.item(self._kitchen.count() - 1)
        if last is not None and last.text() == message:
            return
        self._kitchen.addItem(message)
        self._kitchen.scrollToBottom()

    def _on_batch_progress(self, n: int, total: int, count: int, hint: int) -> None:
        if total:
            self._batch_label.setText(f"Bab {n} dari {total}")
            self._progress_bar.setRange(0, total)
            self._progress_bar.setValue(n)
            elapsed = time.monotonic() - self._started_at
            per_batch = elapsed / max(1, n)
            remaining = int(per_batch * max(0, total - n))
            self._eta_label.setText(f"±{remaining} detik lagi" if remaining else "hampir selesai")

    def _on_error(self, message: str) -> None:
        self.narrate.emit(f"Gagal: {message}")
        self._wrap_up(False)

    def _wrap_up(self, cancelled: bool) -> None:
        if self._done_generating:
            return
        self._done_generating = True
        self._flush_queue()
        self._cancel_button.setEnabled(False)
        self.finished.emit(cancelled)
