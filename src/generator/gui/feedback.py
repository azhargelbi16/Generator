"""Util umpan balik kecil: tooltip saat kursor diam + toast singkat di pojok jendela."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class ToolTip:
    """Kotak info kecil muncul setelah kursor diam ~0,5 detik di atas widget."""

    def __init__(self, widget: tk.Widget, text: str):
        self._widget = widget
        self._text = text
        self._after_id = None
        self._tip = None
        widget.bind("<Enter>", self._jadwal, add="+")
        widget.bind("<Leave>", self._sembunyi, add="+")

    def _jadwal(self, _event=None) -> None:
        self._after_id = self._widget.after(500, self._tampil)

    def _tampil(self) -> None:
        if not self._widget.winfo_exists():
            return
        try:
            x = self._widget.winfo_rootx() + 20
            y = self._widget.winfo_rooty() + self._widget.winfo_height() + 6
            self._tip = tk.Toplevel(self._widget)
            self._tip.overrideredirect(True)
            self._tip.attributes("-topmost", True)
            label = ttk.Label(
                self._tip,
                text=self._text,
                padding=(8, 4),
                style="Tip.TLabel",
                wraplength=260,
            )
            label.pack()
            self._tip.geometry(f"+{x}+{y}")
        except tk.TclError:
            self._tip = None

    def _sembunyi(self, _event=None) -> None:
        if self._after_id is not None:
            try:
                self._widget.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None
        if self._tip is not None:
            try:
                self._tip.destroy()
            except tk.TclError:
                pass
            self._tip = None


class Toast:
    """Pemberitahuan singkat di pojok kanan bawah jendela, hilang sendiri."""

    def __init__(self, root: tk.Misc, text: str, detik: float = 2.0):
        try:
            popup = tk.Toplevel(root)
            popup.overrideredirect(True)
            popup.attributes("-topmost", True)
            ttk.Label(popup, text=text, padding=(14, 8), style="Toast.TLabel").pack()
            popup.update_idletasks()
            lebar = popup.winfo_width()
            tinggi = popup.winfo_height()
            root.update_idletasks()
            x = root.winfo_rootx() + root.winfo_width() - lebar - 24
            y = root.winfo_rooty() + root.winfo_height() - tinggi - 48
            popup.geometry(f"+{x}+{y}")

            def _tutup() -> None:
                try:
                    popup.destroy()
                except tk.TclError:
                    pass

            popup.after(int(detik * 1000), _tutup)
        except tk.TclError:
            pass


def siapkan_gaya(root: tk.Misc) -> None:
    """Gaya khusus tooltip, toast, dan tombol berbahaya yang serasi dengan tema terang aplikasi."""
    gaya = ttk.Style(root)
    gaya.configure("Tip.TLabel", font=("Segoe UI", 9), foreground="#dddddd", background="#3b3b3b")
    gaya.configure("Toast.TLabel", font=("Segoe UI", 9, "bold"))
    gaya.configure("Danger.TButton", background="#c0392b", foreground="#ffffff")
    gaya.map(
        "Danger.TButton",
        background=[("active", "#a93226"), ("pressed", "#922b21")],
        foreground=[("active", "#ffffff"), ("pressed", "#ffffff")],
    )
