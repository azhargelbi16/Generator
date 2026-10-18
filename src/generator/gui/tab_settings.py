"""Tab Pengaturan: endpoint AI, API key, model, temperatur, dan tes koneksi (15, 20)."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ..ai import client
from ..config import Config, load_config, save_config
from .worker import run_in_thread

_PRIVACY_NOTE = (
    "Catatan: API key disimpan apa adanya (belum terenkripsi) di config.json, dan teks "
    "sumber dokumen/web akan dikirim ke layanan AI pada endpoint di atas saat membuat laporan."
)


class SettingsTab(ttk.Frame):
    """Form pengaturan layanan AI dengan Simpan dan Tes Koneksi."""

    def __init__(self, parent, config_path: Path):
        super().__init__(parent, padding=12)
        self._config_path = Path(config_path)

        form = ttk.LabelFrame(self, text="Layanan AI (OpenAI-compatible)")
        form.pack(fill="x")

        self._base_url = tk.StringVar()
        self._api_key = tk.StringVar()
        self._model = tk.StringVar()
        self._temperature = tk.StringVar()
        self._show_key = tk.BooleanVar(value=False)

        rows = [
            ("URL endpoint", self._base_url, "mis. http://localhost:1234/v1"),
            ("Model", self._model, "mis. gpt-4o-mini"),
            ("Temperatur (0,0 - 2,0)", self._temperature, "mis. 0.2"),
        ]
        for row, (label, var, hint) in enumerate(rows):
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", padx=6, pady=4)
            ttk.Entry(form, textvariable=var, width=52).grid(row=row, column=1, columnspan=2, pady=4)
            ttk.Label(form, text=hint, foreground="#666666").grid(row=row, column=3, sticky="w", padx=6)

        ttk.Label(form, text="API key").grid(row=3, column=0, sticky="w", padx=6, pady=4)
        self._key_entry = ttk.Entry(form, textvariable=self._api_key, width=52, show="*")
        self._key_entry.grid(row=3, column=1, pady=4)
        ttk.Checkbutton(form, text="Tampilkan", variable=self._show_key, command=self._toggle_key).grid(
            row=3, column=2, sticky="w"
        )

        buttons = ttk.Frame(self)
        buttons.pack(fill="x", pady=8)
        ttk.Button(buttons, text="Simpan", command=self._save).pack(side="left", padx=4)
        ttk.Button(buttons, text="Tes Koneksi", command=self._test).pack(side="left", padx=4)
        self._status = ttk.Label(buttons, text="")
        self._status.pack(side="left", padx=12)

        ttk.Label(self, text=_PRIVACY_NOTE, foreground="#666666", wraplength=760, justify="left").pack(
            fill="x", pady=(6, 0)
        )

        self._load()

    def _load(self) -> None:
        cfg = load_config(self._config_path)
        self._base_url.set(cfg.ai_base_url)
        self._api_key.set(cfg.ai_api_key)
        self._model.set(cfg.ai_model)
        self._temperature.set(str(cfg.ai_temperature))

    def _toggle_key(self) -> None:
        self._key_entry.config(show="" if self._show_key.get() else "*")

    def _current_config(self) -> Config | None:
        try:
            temperature = float(self._temperature.get().strip().replace(",", "."))
        except ValueError:
            self._status.config(text="Temperatur harus berupa angka, mis. 0.2")
            return None
        return Config(
            ai_base_url=self._base_url.get().strip(),
            ai_api_key=self._api_key.get().strip(),
            ai_model=self._model.get().strip(),
            ai_temperature=temperature,
        )

    def _save(self) -> None:
        cfg = self._current_config()
        if cfg is None:
            return
        save_config(cfg, self._config_path)
        self._status.config(text="Pengaturan tersimpan.")

    def _test(self) -> None:
        cfg = self._current_config()
        if cfg is None:
            return
        self._status.config(text="Menguji koneksi...")

        def work():
            return client.check_connection(client.AIClient(cfg))

        def on_success(result) -> None:
            ok, message = result
            if ok:
                self._status.config(text=f"Koneksi berhasil ({cfg.ai_model}).")
            else:
                self._status.config(text=f"Gagal: {message}")

        def on_error(error) -> None:
            self._status.config(text=f"Gagal: {error}")

        run_in_thread(self, work, on_success=on_success, on_error=on_error)
