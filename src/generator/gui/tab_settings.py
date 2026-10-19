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

_PESAN_SUHU_ANGKA = "Temperatur harus berupa angka, mis. 0.2"
_PESAN_SUHU_RENTANG = "Temperatur harus di antara 0 dan 2"


def parse_temperature(text: str) -> float:
    """Terima koma atau titik desimal; tolak bukan angka dan nilai di luar 0-2."""
    try:
        temperature = float(text.strip().replace(",", "."))
    except ValueError:
        raise ValueError(_PESAN_SUHU_ANGKA) from None
    if not 0.0 <= temperature <= 2.0:
        raise ValueError(_PESAN_SUHU_RENTANG)
    return temperature


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
        self._entry_temperatur = None
        self._petunjuk_temperatur = None
        for row, (label, var, hint) in enumerate(rows):
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", padx=6, pady=4)
            entry = ttk.Entry(form, textvariable=var, width=52)
            entry.grid(row=row, column=1, columnspan=2, pady=4)
            petunjuk = ttk.Label(form, text=hint, foreground="#666666")
            petunjuk.grid(row=row, column=3, sticky="w", padx=6)
            if label.startswith("Temperatur"):
                self._entry_temperatur = entry
                self._petunjuk_temperatur = petunjuk
                entry.bind("<KeyRelease>", self._cek_suhu_langsung)
                entry.bind("<FocusOut>", self._cek_suhu_langsung)

        ttk.Label(form, text="API key").grid(row=3, column=0, sticky="w", padx=6, pady=4)
        self._key_entry = ttk.Entry(form, textvariable=self._api_key, width=52, show="*")
        self._key_entry.grid(row=3, column=1, pady=4)
        ttk.Checkbutton(form, text="Tampilkan", variable=self._show_key, command=self._toggle_key).grid(
            row=3, column=2, sticky="w"
        )

        buttons = ttk.Frame(self)
        buttons.pack(fill="x", pady=8)
        ttk.Button(buttons, text="Simpan", command=self._save).pack(side="left", padx=4)
        self._tombol_tes = ttk.Button(buttons, text="Tes Koneksi", command=self._test)
        self._tombol_tes.pack(side="left", padx=4)
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
            temperature = parse_temperature(self._temperature.get())
        except ValueError as error:
            self._status.config(text=str(error))
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

    def _cek_suhu_langsung(self, _event=None) -> None:
        """Peringatan segera saat mengetik: petunjuk merah jika suhu tidak sah."""
        if self._petunjuk_temperatur is None:
            return
        try:
            parse_temperature(self._temperature.get())
        except ValueError as error:
            self._petunjuk_temperatur.config(text=str(error), foreground="#b00020")
        else:
            self._petunjuk_temperatur.config(text="mis. 0.2", foreground="#666666")

    def _test(self) -> None:
        cfg = self._current_config()
        if cfg is None:
            return
        self._status.config(text="Menguji koneksi...")
        self._tombol_tes.config(state="disabled", text="Menguji...")

        def work():
            return client.check_connection(client.AIClient(cfg))

        def on_success(result) -> None:
            ok, message = result
            if ok:
                self._status.config(text=f"Koneksi berhasil ({cfg.ai_model}).")
            else:
                self._status.config(text=f"Gagal: {message}")
            self._tombol_tes.config(state="normal", text="Tes Koneksi")

        def on_error(error) -> None:
            self._status.config(text=f"Gagal: {error}")
            self._tombol_tes.config(state="normal", text="Tes Koneksi")

        run_in_thread(self, work, on_success=on_success, on_error=on_error)
