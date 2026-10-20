from __future__ import annotations


def test_qt_package_imports_without_display():
    import generator.qt

    assert generator.qt.__doc__
