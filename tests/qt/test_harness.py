from __future__ import annotations


def test_offscreen_platform_active(qapp):
    from PySide6.QtWidgets import QMainWindow

    w = QMainWindow()
    w.show()
    qapp.processEvents()
    assert w.isVisible()
