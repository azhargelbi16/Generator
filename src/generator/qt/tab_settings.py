"""Tab Pengaturan Qt: endpoint AI, API key, model, temperatur, tes koneksi (parity gui/tab_settings.py).

Baru dibanding Tk: petunjuk inline saat URL tidak diakhiri /v1 dan tombol
"Ambil model..." yang mengisi combo model dari GET {base}/models (Task 2.5).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import paths
from ..ai import client
from ..config import Config, load_config, parse_temperature, save_config
from .workers import run_in_thread

_PRIVACY_NOTE = (
    "Catatan: API key disimpan apa adanya (belum terenkripsi) di config.json, dan teks "
    "sumber dokumen/web akan dikirim ke layanan AI pada endpoint di atas saat membuat laporan."
)

_HINT_SUHU_DEFAULT = "mis. 0.2"
_PETUNJUK_V1 = "Base URL harus sampai /v1 (mis. http://localhost:1234/v1)"


class SettingsTab(QWidget):
    """Form pengaturan layanan AI dengan Simpan, Tes Koneksi, dan Ambil model."""

    def __init__(self, config_path: Path | None = None):
        super().__init__()
        self._config_path = Path(config_path) if config_path else Path(paths.CONFIG_PATH)
        self._thread = None
        self._worker = None
        # Titik injeksi tes; produksi memakai client.check_connection.
        self._test_connection = client.check_connection

        self._fields: dict[str, QWidget] = {
            "base_url": QLineEdit(),
            "model": QComboBox(),
            "temperature": QLineEdit(),
            "api_key": QLineEdit(),
        }
        self._fields["model"].setEditable(True)

        form = QFormLayout()
        form.addRow("URL endpoint", self._fields["base_url"])
        self._url_hint = QLabel("")
        self._url_hint.setStyleSheet("color: #b00020;")
        form.addRow("", self._url_hint)
        form.addRow("Model", self._fields["model"])
        form.addRow("Temperatur (0,0 - 2,0)", self._fields["temperature"])
        self._hint_temperature = QLabel(_HINT_SUHU_DEFAULT)
        self._hint_temperature.setStyleSheet("color: #666666;")
        form.addRow("", self._hint_temperature)
        self._fields["temperature"].textChanged.connect(self._cek_suhu_langsung)
        key_row = QHBoxLayout()
        key_row.addWidget(self._fields["api_key"], stretch=1)
        self._show_key = QCheckBox("Tampilkan")
        self._show_key.toggled.connect(
            lambda checked: self._fields["api_key"].setEchoMode(
                QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
            )
        )
        key_row.addWidget(self._show_key)
        form.addRow("API key", key_row)

        buttons = QHBoxLayout()
        save = QPushButton("Simpan")
        save.clicked.connect(self._save)
        test = QPushButton("Tes Koneksi")
        test.clicked.connect(self._test)
        fetch = QPushButton("Ambil model...")
        fetch.clicked.connect(self._fetch_models)
        buttons.addWidget(save)
        buttons.addWidget(test)
        buttons.addWidget(fetch)
        buttons.addStretch(1)
        self._status = QLabel("")
        buttons.addWidget(self._status)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(buttons)
        privacy = QLabel(_PRIVACY_NOTE)
        privacy.setStyleSheet("color: #666666;")
        privacy.setWordWrap(True)
        layout.addWidget(privacy)
        layout.addStretch(1)

        self._config = load_config(self._config_path)
        self._load()

    def _load(self) -> None:
        self._fields["base_url"].setText(self._config.ai_base_url)
        self._fields["api_key"].setText(self._config.ai_api_key)
        self._fields["model"].setCurrentText(self._config.ai_model)
        self._fields["temperature"].setText(str(self._config.ai_temperature))

    def _cek_suhu_langsung(self) -> None:
        """Peringatan segera saat mengetik: petunjuk merah jika suhu tidak sah."""
        try:
            parse_temperature(self._fields["temperature"].text())
        except ValueError as error:
            self._hint_temperature.setText(str(error))
            self._hint_temperature.setStyleSheet("color: #b00020;")
        else:
            self._hint_temperature.setText(_HINT_SUHU_DEFAULT)
            self._hint_temperature.setStyleSheet("color: #666666;")

    def _current_config(self) -> Config | None:
        try:
            temperature = parse_temperature(self._fields["temperature"].text())
        except ValueError as error:
            self._status.setText(str(error))
            return None
        return Config(
            ai_base_url=self._fields["base_url"].text().strip(),
            ai_api_key=self._fields["api_key"].text().strip(),
            ai_model=self._fields["model"].currentText().strip(),
            ai_temperature=temperature,
            citation_style=self._config.citation_style,
            dosen_review=self._config.dosen_review,
        )

    def _save(self) -> None:
        cfg = self._current_config()
        if cfg is None:
            return
        save_config(cfg, self._config_path)
        self._config = cfg
        self._status.setText("Pengaturan tersimpan.")

    def _test(self) -> None:
        cfg = self._current_config()
        if cfg is None:
            return
        self._status.setText("Menguji koneksi...")
        self._thread, self._worker = run_in_thread(
            self, lambda: self._test_connection(client.AIClient(cfg))
        )
        self._worker.result.connect(lambda result: self._on_test_result(cfg, result))
        self._worker.error.connect(lambda message: self._status.setText(f"Gagal: {message}"))

    def _on_test_result(self, cfg: Config, result) -> None:
        ok, message = result
        if ok:
            self._status.setText(f"Koneksi berhasil ({cfg.ai_model}).")
            self._url_hint.setText("")
            return
        self._status.setText(f"Gagal: {message}")
        if not cfg.ai_base_url.rstrip("/").endswith("/v1"):
            self._url_hint.setText(_PETUNJUK_V1)
        else:
            self._url_hint.setText("")

    def _fetch_models(self) -> None:
        cfg = self._current_config()
        if cfg is None:
            return
        self._status.setText("Mengambil daftar model...")
        self._thread, self._worker = run_in_thread(self, lambda: client.list_models(cfg))
        self._worker.result.connect(self._on_models)
        self._worker.error.connect(
            lambda message: self._status.setText(f"Gagal: {message}")
        )

    def _on_models(self, models: list[str]) -> None:
        self._fields["model"].clear()
        self._fields["model"].addItems(models)
        self._status.setText(f"{len(models)} model ditemukan.")
