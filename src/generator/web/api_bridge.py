"""API Bridge connecting pywebview frontend to Generator Laporan core logic."""

from __future__ import annotations

import json
import logging
import os
import shutil
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Any

import webview

from .. import atomic, config, database, drafts, format_spec, paths, preflight, report
from ..ai import bibliography, content, citation, client, dosen
from ..ai.citation import Source, Author
from ..ai.client import AIClient, AIError
from ..document import renderer, template, placeholders
from ..sources import pdf_reader, web_reader, doi_resolver
from ..sources.records import (
    DRAFT_ACTIVE_ID,
    normalize_metadata,
    record_to_source,
    source_to_record,
)
from ..verification import verify_sections, STATUS_VERIFIED, STATUS_NEEDS_REVIEW, STATUS_UNVERIFIED, STATUS_NON_FACTUAL

log = logging.getLogger("generator.web.api")


class ApiBridge:
    """Methods exposed to JavaScript via window.pywebview.api.*"""

    def __init__(self, db: database.Database, config_path: Path | None = None):
        self.db = db
        self.config_path = Path(config_path) if config_path else Path(paths.CONFIG_PATH)
        self._cfg = config.load_config(self.config_path)
        self._window: webview.Window | None = None
        self._cancel_gen_event = threading.Event()
        self._gen_thread: threading.Thread | None = None

    def set_window(self, window: webview.Window) -> None:
        self._window = window

    def _emit(self, event_name: str, payload: Any = None) -> None:
        """Emit custom DOM event to the frontend."""
        if not self._window:
            return
        data_json = json.dumps(payload or {})
        script = f"window.dispatchEvent(new CustomEvent('{event_name}', {{detail: {data_json}}}));"
        try:
            self._window.evaluate_js(script)
        except Exception as e:
            log.warning(f"Failed to emit JS event {event_name}: {e}")

    # =========================================================================
    # CONFIG & AI SERVICE
    # =========================================================================

    def get_config(self) -> dict[str, Any]:
        self._cfg = config.load_config(self.config_path)
        data = asdict(self._cfg)
        data["ai_api_key_set"] = bool(self._cfg.ai_api_key and self._cfg.ai_api_key.strip())
        data["ai_api_key"] = ""
        return data

    def save_config(self, cfg_data: dict[str, Any]) -> dict[str, Any]:
        try:
            temp = float(str(cfg_data.get("ai_temperature", 0.2)).replace(",", "."))
            temp = max(0.0, min(2.0, temp))
        except (ValueError, TypeError):
            temp = 0.2

        new_key = str(cfg_data.get("ai_api_key", "")).strip()
        if not new_key:
            api_key = self._cfg.ai_api_key
        else:
            api_key = new_key

        self._cfg = config.Config(
            ai_base_url=str(cfg_data.get("ai_base_url", "http://localhost:1234/v1")).strip(),
            ai_api_key=api_key,
            ai_model=str(cfg_data.get("ai_model", "gpt-4o-mini")).strip(),
            ai_temperature=temp,
            citation_style=str(cfg_data.get("citation_style", "et_al")),
            dosen_review=bool(cfg_data.get("dosen_review", False)),
        )
        config.save_config(self._cfg, self.config_path)
        res_data = asdict(self._cfg)
        res_data["ai_api_key_set"] = bool(self._cfg.ai_api_key and self._cfg.ai_api_key.strip())
        res_data["ai_api_key"] = ""
        return {"success": True, "config": res_data}

    def test_ai_connection(self, base_url: str | None = None, api_key: str | None = None, model: str | None = None) -> dict[str, Any]:
        key_to_use = str(api_key).strip() if (api_key and str(api_key).strip()) else self._cfg.ai_api_key
        test_cfg = config.Config(
            ai_base_url=str(base_url if base_url else self._cfg.ai_base_url).strip(),
            ai_api_key=key_to_use,
            ai_model=str(model if model is not None else self._cfg.ai_model).strip(),
            ai_temperature=self._cfg.ai_temperature,
            citation_style=self._cfg.citation_style,
            dosen_review=self._cfg.dosen_review,
        )
        cl = AIClient(test_cfg)
        ok, msg = client.check_connection(cl)
        return {"ok": ok, "message": msg}

    def fetch_models(self, base_url: str | None = None, api_key: str | None = None) -> dict[str, Any]:
        key_to_use = str(api_key).strip() if (api_key and str(api_key).strip()) else self._cfg.ai_api_key
        test_cfg = config.Config(
            ai_base_url=str(base_url if base_url else self._cfg.ai_base_url).strip(),
            ai_api_key=key_to_use,
            ai_model=self._cfg.ai_model,
            ai_temperature=self._cfg.ai_temperature,
            citation_style=self._cfg.citation_style,
            dosen_review=self._cfg.dosen_review,
        )
        try:
            models = client.list_models(test_cfg)
            return {"ok": True, "models": models}
        except Exception as e:
            return {"ok": False, "error": str(e), "models": []}

    # =========================================================================
    # DATABASE & ENTITIES
    # =========================================================================

    def get_profile(self) -> dict[str, str]:
        p = self.db.get_profil()
        return {"nama": p.nama, "nim": p.nim, "prodi": p.prodi}

    def save_profile(self, data: dict[str, str]) -> dict[str, Any]:
        self.db.set_profil(
            database.Profil(
                nama=str(data.get("nama", "")).strip(),
                nim=str(data.get("nim", "")).strip(),
                prodi=str(data.get("prodi", "")).strip(),
            )
        )
        return {"success": True}

    def list_dosen(self) -> list[dict[str, Any]]:
        return [asdict(d) for d in self.db.list_dosen()]

    def add_dosen(self, d: dict[str, Any]) -> dict[str, Any]:
        dosen_obj = database.Dosen(
            id=0,
            nama=str(d.get("nama", "")).strip(),
            gelar=str(d.get("gelar", "")).strip(),
            identitas=str(d.get("identitas", "")).strip(),
        )
        new_id = self.db.add_dosen(dosen_obj)
        return {"success": True, "dosen": {"id": new_id, "nama": dosen_obj.nama, "gelar": dosen_obj.gelar, "identitas": dosen_obj.identitas}}

    def update_dosen(self, d: dict[str, Any]) -> dict[str, Any]:
        dosen_obj = database.Dosen(
            id=int(d["id"]),
            nama=str(d.get("nama", "")).strip(),
            gelar=str(d.get("gelar", "")).strip(),
            identitas=str(d.get("identitas", "")).strip(),
        )
        self.db.update_dosen(dosen_obj)
        return {"success": True}

    def delete_dosen(self, dosen_id: int) -> dict[str, Any]:
        self.db.delete_dosen(int(dosen_id))
        return {"success": True}

    def list_matkul(self) -> list[dict[str, Any]]:
        return [asdict(m) for m in self.db.list_mata_kuliah()]

    def add_matkul(self, m: dict[str, Any]) -> dict[str, Any]:
        matkul_obj = database.MataKuliah(
            id=0,
            nama=str(m.get("nama", "")).strip(),
            kode=str(m.get("kode", "")).strip(),
        )
        new_id = self.db.add_mata_kuliah(matkul_obj)
        return {"success": True, "matkul": {"id": new_id, "nama": matkul_obj.nama, "kode": matkul_obj.kode}}

    def update_matkul(self, m: dict[str, Any]) -> dict[str, Any]:
        matkul_obj = database.MataKuliah(
            id=int(m["id"]),
            nama=str(m.get("nama", "")).strip(),
            kode=str(m.get("kode", "")).strip(),
        )
        self.db.update_mata_kuliah(matkul_obj)
        return {"success": True}

    def delete_matkul(self, mk_id: int) -> dict[str, Any]:
        self.db.delete_mata_kuliah(int(mk_id))
        return {"success": True}

    def list_logos(self) -> list[dict[str, Any]]:
        logos = self.db.list_logo()
        res = []
        for l in logos:
            exists = Path(l.path).is_file()
            res.append({"id": l.id, "nama": l.nama, "path": l.path, "exists": exists})
        return res

    def upload_logo(self) -> dict[str, Any]:
        if not self._window:
            return {"cancelled": True}
        file_types = ("Image files (*.png;*.jpg;*.jpeg;*.bmp)", "All files (*.*)")
        res = self._window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False, file_types=file_types)
        if not res or len(res) == 0:
            return {"cancelled": True}

        src_path = Path(res[0])
        paths.LOGOS_DIR.mkdir(parents=True, exist_ok=True)
        dest_path = paths.LOGOS_DIR / src_path.name
        counter = 1
        while dest_path.exists():
            dest_path = paths.LOGOS_DIR / f"{src_path.stem}_{counter}{src_path.suffix}"
            counter += 1

        shutil.copy2(src_path, dest_path)
        logo_id = self.db.add_logo(database.Logo(0, src_path.stem, str(dest_path)))
        return {"success": True, "logo": {"id": logo_id, "nama": src_path.stem, "path": str(dest_path), "exists": True}}

    def delete_logo(self, logo_id: int) -> dict[str, Any]:
        logos = self.db.list_logo()
        found = next((l for l in logos if l.id == int(logo_id)), None)
        if found and Path(found.path).is_file():
            try:
                Path(found.path).unlink(missing_ok=True)
            except Exception:
                pass
        self.db.delete_logo(int(logo_id))
        return {"success": True}

    # =========================================================================
    # TEMPLATES
    # =========================================================================

    def _create_academic_template_docx(self, dest_path: Path, options: dict[str, Any] | None = None) -> None:
        from docx import Document
        from docx.shared import Cm, Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.enum.style import WD_STYLE_TYPE

        opts = options or {}
        font_name = opts.get("font_name", "Times New Roman")
        margin_preset = opts.get("margin_preset", "4433")
        line_spacing = float(opts.get("line_spacing", 1.5))

        doc = Document()

        # 1. Dimensi Kertas A4 (21.0 x 29.7 cm) & Margin Baku
        section = doc.sections[0]
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        if margin_preset == "4433":
            # Standar Skripsi/Tesis Dikti: Kiri 4 cm, Atas 4 cm, Kanan 3 cm, Bawah 3 cm
            section.top_margin = Cm(4.0)
            section.left_margin = Cm(4.0)
            section.right_margin = Cm(3.0)
            section.bottom_margin = Cm(3.0)
        else:
            # Standar Makalah/Artikel Bebas: 3 cm sekeliling
            section.top_margin = Cm(3.0)
            section.left_margin = Cm(3.0)
            section.right_margin = Cm(3.0)
            section.bottom_margin = Cm(3.0)

        # 2. Tipografi Baku
        normal = doc.styles["Normal"]
        normal.font.name = font_name
        normal.font.size = Pt(12)
        normal.font.color.rgb = RGBColor(0, 0, 0)
        normal.paragraph_format.line_spacing = line_spacing
        normal.paragraph_format.space_after = Pt(0)

        if "Heading 1" in doc.styles:
            h1 = doc.styles["Heading 1"]
        else:
            h1 = doc.styles.add_style("Heading 1", WD_STYLE_TYPE.PARAGRAPH)
        h1.font.name = font_name
        h1.font.size = Pt(14)
        h1.font.bold = True
        h1.font.color.rgb = RGBColor(0, 0, 0)
        h1.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        h1.paragraph_format.space_before = Pt(12)
        h1.paragraph_format.space_after = Pt(6)
        h1.paragraph_format.line_spacing = line_spacing

        if "Heading 2" in doc.styles:
            h2 = doc.styles["Heading 2"]
        else:
            h2 = doc.styles.add_style("Heading 2", WD_STYLE_TYPE.PARAGRAPH)
        h2.font.name = font_name
        h2.font.size = Pt(12)
        h2.font.bold = True
        h2.font.color.rgb = RGBColor(0, 0, 0)
        h2.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        h2.paragraph_format.space_before = Pt(6)
        h2.paragraph_format.space_after = Pt(4)
        h2.paragraph_format.line_spacing = line_spacing

        # 3. Halaman Sampul (Cover Page)
        p_judul = doc.add_paragraph()
        p_judul.paragraph_format.space_before = Cm(1.5)
        p_judul.paragraph_format.space_after = Cm(1.0)
        p_judul.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_judul = p_judul.add_run("{{JUDUL}}")
        r_judul.bold = True
        r_judul.font.name = font_name
        r_judul.font.size = Pt(16)

        p_jenis = doc.add_paragraph()
        p_jenis.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_jenis.paragraph_format.space_after = Cm(1.5)
        r_jenis = p_jenis.add_run("LAPORAN AKADEMIK")
        r_jenis.bold = True
        r_jenis.font.name = font_name
        r_jenis.font.size = Pt(12)

        p_logo = doc.add_paragraph("{{LOGO}}")
        p_logo.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_logo.paragraph_format.space_after = Cm(2.0)

        p_meta = doc.add_paragraph()
        p_meta.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_meta.paragraph_format.line_spacing = 1.15

        r_oleh = p_meta.add_run("Disusun Oleh:\n")
        r_oleh.bold = True
        r_oleh.font.name = font_name
        r_oleh.font.size = Pt(12)

        r_mhs = p_meta.add_run("Nama: {{NAMA}}\nNIM: {{NIM}}\n\n")
        r_mhs.font.name = font_name
        r_mhs.font.size = Pt(12)

        r_dos_label = p_meta.add_run("Dosen Pembimbing:\n")
        r_dos_label.bold = True
        r_dos_label.font.name = font_name
        r_dos_label.font.size = Pt(12)

        r_dos = p_meta.add_run("{{DOSEN}}\n\n")
        r_dos.font.name = font_name
        r_dos.font.size = Pt(12)

        r_mk = p_meta.add_run("Mata Kuliah: {{MATA_KULIAH}}\n")
        r_mk.font.name = font_name
        r_mk.font.size = Pt(12)

        r_tgl = p_meta.add_run("{{TANGGAL}}")
        r_tgl.font.name = font_name
        r_tgl.font.size = Pt(12)

        doc.add_page_break()

        # 4. Halaman Daftar Isi
        h_toc = doc.add_paragraph(style="Heading 1")
        r_toc = h_toc.add_run("DAFTAR ISI")
        r_toc.bold = True
        h_toc.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER

        p_toc = doc.add_paragraph("{{DAFTAR_ISI}}")
        p_toc.paragraph_format.space_before = Pt(12)

        doc.add_page_break()

        # 5. Halaman Isi Laporan
        doc.add_paragraph("{{ISI_LAPORAN}}")

        doc.add_page_break()

        # 6. Halaman Daftar Pustaka
        h_pus = doc.add_paragraph(style="Heading 1")
        r_pus = h_pus.add_run("DAFTAR PUSTAKA")
        r_pus.bold = True
        h_pus.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER

        p_pus = doc.add_paragraph("{{DAFTAR_PUSTAKA}}")
        p_pus.paragraph_format.space_before = Pt(12)

        doc.save(dest_path)

    def _ensure_default_template(self) -> None:
        try:
            paths.TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
            dest_path = paths.TEMPLATES_DIR / "Template_Standar_Akademik.docx"
            if not dest_path.is_file():
                self._create_academic_template_docx(dest_path)

            all_tpls = self.db.list_template()
            desc = "Template Word resmi baku (Margin 4-4-3-3 cm, Times New Roman 12pt, Cover, TOC, APA 7)"
            if not any(Path(t.path).resolve() == dest_path.resolve() for t in all_tpls):
                self.db.add_template(database.Template(
                    0,
                    "Template Standar Akademik",
                    desc,
                    str(dest_path)
                ))
        except Exception as e:
            log.warning(f"Gagal memastikan template default: {e}")

    def create_default_template(self, options: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            paths.TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
            dest_path = paths.TEMPLATES_DIR / "Template_Standar_Akademik.docx"
            self._create_academic_template_docx(dest_path, options)

            all_tpls = self.db.list_template()
            existing = next((t for t in all_tpls if Path(t.path).resolve() == dest_path.resolve()), None)
            desc = "Template Word resmi baku (Margin 4-4-3-3 cm, Times New Roman 12pt, Cover, TOC, APA 7)"
            if existing:
                self.db.update_template(database.Template(
                    existing.id,
                    "Template Standar Akademik",
                    desc,
                    str(dest_path)
                ))
            else:
                self.db.add_template(database.Template(
                    0,
                    "Template Standar Akademik",
                    desc,
                    str(dest_path)
                ))
            return {"success": True, "path": str(dest_path)}
        except Exception as e:
            log.exception("Gagal membuat template standar")
            return {"success": False, "error": str(e)}

    def open_template(self, template_id: int) -> dict[str, Any]:
        tpl = next((t for t in self.db.list_template() if t.id == int(template_id)), None)
        if not tpl:
            return {"success": False, "error": "Template tidak ditemukan"}
        p = Path(tpl.path)
        if not p.is_file():
            return {"success": False, "error": f"Berkas tidak ditemukan: {p}"}
        if os.name == "nt":
            try:
                os.startfile(str(p.resolve()))
                return {"success": True}
            except Exception as e:
                return {"success": False, "error": f"Gagal membuka aplikasi Word: {e}"}
        return {"success": True}

    def open_templates_folder(self) -> dict[str, Any]:
        try:
            paths.TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
            if os.name == "nt":
                os.startfile(str(paths.TEMPLATES_DIR.resolve()))
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": f"Gagal membuka folder template: {e}"}

    def list_templates(self) -> list[dict[str, Any]]:
        templates = self.db.list_template()
        if not templates:
            self._ensure_default_template()
            templates = self.db.list_template()
        results = []
        for t in templates:
            p = Path(t.path)
            status = "berkas_hilang"
            missing: list[str] = []
            not_standalone: list[str] = []
            unknown: list[str] = []
            placeholders_list: list[str] = []

            if p.is_file():
                try:
                    res = template.validate_template(p)
                    missing = list(res.missing)
                    not_standalone = list(res.not_standalone)
                    unknown = list(res.unknown)
                    status = "lengkap" if res.is_processable else "tidak_lengkap"
                    doc = template.load_template(p)
                    placeholders_list = placeholders.collect_names(doc)
                except Exception as e:
                    status = f"rusak: {e}"

            is_default = "Template_Standar_Akademik" in str(p.name) or "Standar" in t.nama
            results.append({
                "id": t.id,
                "nama": t.nama,
                "deskripsi": t.deskripsi,
                "path": t.path,
                "status": status,
                "missing": missing,
                "not_standalone": not_standalone,
                "unknown": unknown,
                "placeholders": placeholders_list,
                "is_default": is_default,
                "spec": {
                    "paper": "A4",
                    "margin": "4-4-3-3 cm" if is_default else "Sesuai File",
                    "font": "Times New Roman 12pt" if is_default else "Sesuai File",
                    "spacing": "1.5" if is_default else "Sesuai File",
                },
            })
        return results

    def upload_template(self) -> dict[str, Any]:
        if not self._window:
            return {"cancelled": True}
        file_types = ("Word Document (*.docx)", "All files (*.*)")
        res = self._window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False, file_types=file_types)
        if not res or len(res) == 0:
            return {"cancelled": True}

        src_path = Path(res[0])
        paths.TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
        dest_path = paths.TEMPLATES_DIR / src_path.name
        counter = 1
        while dest_path.exists():
            dest_path = paths.TEMPLATES_DIR / f"{src_path.stem}_{counter}{src_path.suffix}"
            counter += 1

        shutil.copy2(src_path, dest_path)
        try:
            val_result = template.validate_template(dest_path)
        except template.TemplateError as exc:
            try:
                dest_path.unlink(missing_ok=True)
            except OSError:
                pass
            return {"error": f"Berkas template tidak valid atau rusak: {exc}"}
        tpl_id = self.db.add_template(database.Template(0, src_path.stem, "Diimpor pengguna", str(dest_path)))

        return {
            "success": True,
            "template": {
                "id": tpl_id,
                "nama": src_path.stem,
                "path": str(dest_path),
                "is_processable": val_result.is_processable,
                "missing": list(val_result.missing),
                "not_standalone": list(val_result.not_standalone),
                "unknown": list(val_result.unknown),
            }
        }

    def delete_template(self, template_id: int) -> dict[str, Any]:
        tpls = self.db.list_template()
        found = next((t for t in tpls if t.id == int(template_id)), None)
        if found and Path(found.path).is_file():
            try:
                Path(found.path).unlink(missing_ok=True)
            except Exception:
                pass
        self.db.delete_template(int(template_id))
        return {"success": True}

    # =========================================================================
    # SOURCES (PDF, WEB, MANUAL)
    # =========================================================================

    def pick_pdf_source(self) -> dict[str, Any]:
        if not self._window:
            return {"cancelled": True}
        file_types = ("PDF Files (*.pdf)", "All files (*.*)")
        res = self._window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False, file_types=file_types)
        if not res or len(res) == 0:
            return {"cancelled": True}

        pdf_path = Path(res[0])
        try:
            text = pdf_reader.extract_text_or_ocr(pdf_path)
        except Exception as e:
            return {"error": f"Gagal membaca PDF: {e}"}

        doc_meta = normalize_metadata(pdf_reader.extract_metadata(pdf_path))
        cl = AIClient(self._cfg)
        try:
            source = bibliography.extract_source(text, cl)
        except (AIError, bibliography.BibliographyError):
            source = Source([], "", "")

        merged = bibliography.merge_metadata(source, doc_meta)
        if not merged.title:
            merged = Source(merged.authors, merged.year, pdf_path.stem, merged.container, merged.doi, merged.url)

        record = source_to_record(merged, text, "pdf")
        return {"success": True, "record": record}

    def add_web_source(self, url: str) -> dict[str, Any]:
        url = url.strip()
        if not url:
            return {"error": "URL tidak boleh kosong."}
        try:
            text, meta = web_reader.fetch(url)
            meta = normalize_metadata(meta)
        except Exception as e:
            return {"error": f"Gagal mengambil halaman web: {e}"}

        cl = AIClient(self._cfg)
        try:
            source = bibliography.extract_source(text, cl)
        except (AIError, bibliography.BibliographyError):
            source = Source([], "", "")

        merged = bibliography.merge_metadata(source, meta)
        record = source_to_record(merged, text, "web")
        return {"success": True, "record": record}

    def add_manual_source(self, text: str) -> dict[str, Any]:
        text = text.strip()
        if not text:
            return {"error": "Teks sumber tidak boleh kosong."}

        cl = AIClient(self._cfg)
        try:
            source = bibliography.extract_source(text, cl)
        except (AIError, bibliography.BibliographyError):
            source = Source([], "", "Teks Manual")

        merged = bibliography.merge_metadata(source, {})
        record = source_to_record(merged, text, "manual")
        return {"success": True, "record": record}

    def resolve_doi_source(self, doi: str) -> dict[str, Any]:
        doi = doi.strip()
        if not doi:
            return {"error": "DOI tidak boleh kosong."}
        try:
            record = doi_resolver.fetch_doi_metadata(doi)
            return {"success": True, "record": record}
        except Exception as e:
            return {"error": f"Gagal mengambil metadata DOI: {e}"}

    # =========================================================================
    # FORMATS & OUTLINES
    # =========================================================================

    def get_format_variants(self) -> list[dict[str, Any]]:
        choices = format_spec.variant_choices()
        res = []
        for code, label in choices:
            var = format_spec.get_variant(code)
            if var:
                res.append({
                    "code": var.code,
                    "name": var.name,
                    "description": var.description,
                    "skeleton": format_spec.skeleton_lines(var),
                    "outline_titles": format_spec.outline_titles(var),
                })
            else:
                res.append({
                    "code": "bebas",
                    "name": "Bebas",
                    "description": "Outline manual bebas tanpa struktur baku.",
                    "skeleton": ["Bebas menyusun outline."],
                    "outline_titles": [],
                })
        return res

    def suggest_outline(self, topic: str, sources_data: list[dict[str, Any]]) -> dict[str, Any]:
        topic = topic.strip()
        if not topic:
            return {"error": "Tulis judul laporan terlebih dahulu."}

        sources = [record_to_source(s) for s in sources_data]
        texts = [s.get("text", "") for s in sources_data]
        cl = AIClient(self._cfg)
        try:
            outlines = content.suggest_outline(topic, sources, texts, cl)
            return {"success": True, "outline": outlines}
        except Exception as e:
            return {"error": f"Gagal menyusun outline: {e}"}

    # =========================================================================
    # DRAFTS
    # =========================================================================

    def load_active_draft(self) -> dict[str, Any]:
        draft = drafts.load_draft(DRAFT_ACTIVE_ID)
        if not draft:
            return {"has_draft": False}
        return {
            "has_draft": True,
            "draft_id": draft.draft_id,
            "fields": draft.fields,
            "sources": draft.sources,
            "sections": draft.sections,
            "done": list(draft.done),
        }

    def save_active_draft(self, state: dict[str, Any]) -> dict[str, Any]:
        draft_state = drafts.DraftState(
            draft_id=DRAFT_ACTIVE_ID,
            fields=state.get("fields", {}),
            sources=state.get("sources", []),
            sections=state.get("sections", []),
            done=list(state.get("done", [])),
        )
        drafts.save_draft(draft_state)
        return {"success": True}

    def clear_active_draft(self) -> dict[str, Any]:
        drafts.delete_draft(DRAFT_ACTIVE_ID)
        return {"success": True}

    def list_saved_drafts(self) -> list[dict[str, Any]]:
        draft_ids = drafts.list_drafts()
        results = []
        for d_id in draft_ids:
            st = drafts.load_draft(d_id)
            if not st:
                continue
            title = st.fields.get("JUDUL", "Tanpa Judul") if st.fields else "Tanpa Judul"
            sentence_count = sum(len(p.get("sentences", [])) for sec in st.sections for p in sec.get("paragraphs", []))
            try:
                p = paths.DRAFTS_DIR / f"{d_id}.json"
                mtime = p.stat().st_mtime
            except Exception:
                mtime = 0
            results.append({
                "draft_id": d_id,
                "title": title or "Tanpa Judul",
                "sources_count": len(st.sources),
                "sections_count": len(st.sections),
                "sentence_count": sentence_count,
                "is_active": d_id == DRAFT_ACTIVE_ID,
                "mtime": mtime,
            })
        results.sort(key=lambda x: (not x["is_active"], -x["mtime"]))
        return results

    def save_named_draft(self, name: str, state: dict[str, Any]) -> dict[str, Any]:
        slug = report.sanitize_filename(name, max_len=40)
        if not slug or slug == "laporan":
            slug = f"laporan_{report.sanitize_filename(state.get('fields', {}).get('JUDUL', 'proyek'), max_len=20)}"
        draft_state = drafts.DraftState(
            draft_id=slug,
            fields=state.get("fields", {}),
            sources=state.get("sources", []),
            sections=state.get("sections", []),
            done=list(state.get("done", [])),
        )
        drafts.save_draft(draft_state)
        return {"success": True, "draft_id": slug}

    def load_named_draft(self, draft_id: str) -> dict[str, Any]:
        st = drafts.load_draft(draft_id)
        if not st:
            return {"error": "Draf tidak ditemukan."}
        active_copy = drafts.DraftState(
            draft_id=DRAFT_ACTIVE_ID,
            fields=st.fields,
            sources=st.sources,
            sections=st.sections,
            done=st.done,
        )
        drafts.save_draft(active_copy)
        return {
            "success": True,
            "draft": {
                "has_draft": True,
                "draft_id": st.draft_id,
                "fields": st.fields,
                "sources": st.sources,
                "sections": st.sections,
                "done": list(st.done),
            }
        }

    def delete_named_draft(self, draft_id: str) -> dict[str, Any]:
        drafts.delete_draft(draft_id)
        return {"success": True}

    # =========================================================================
    # GENERATION ORCHESTRATION (STREAMING VIA JS EVENTS)
    # =========================================================================

    def start_generation(self, request_data: dict[str, Any]) -> dict[str, Any]:
        if self._gen_thread and self._gen_thread.is_alive():
            return {"error": "Generasi sedang berjalan."}

        topic = request_data.get("topic", "").strip()
        outline = request_data.get("outline", [])
        sources_data = request_data.get("sources", [])
        variant_code = request_data.get("variant", "b")

        if not topic:
            return {"error": "Judul belum diisi."}
        if not outline:
            return {"error": "Outline masih kosong."}
        if not sources_data:
            return {"error": "Masukkan minimal satu sumber referensi."}

        self._cancel_gen_event.clear()

        sources = [record_to_source(s) for s in sources_data]
        texts = [s.get("text", "") for s in sources_data]
        variant = format_spec.get_variant(variant_code)

        class Progress(content.GenerationProgress):
            def __init__(self, bridge: ApiBridge):
                self.bridge = bridge

            def batch_started(self, n: int, total: int) -> None:
                self.bridge._emit("gen_batch_progress", {"batch": n, "total": total})

            def sentence_born(self, sentence: content.Sentence, status: str) -> None:
                self.bridge._emit("gen_sentence_born", {
                    "uid": sentence.uid,
                    "text": sentence.text,
                    "status": status,
                    "is_factual": sentence.is_factual,
                    "source_ids": sentence.source_ids,
                })

            def finished(self, cancelled: bool) -> None:
                self.bridge._emit("gen_finished", {"cancelled": cancelled})

        def run_thread():
            prog = Progress(self)
            cl = AIClient(self._cfg)
            try:
                sections = content.generate_sections(
                    topic=topic,
                    outline=outline,
                    sources=sources,
                    source_texts=texts,
                    client=cl,
                    progress=prog,
                    cancel=self._cancel_gen_event,
                    variant=variant,
                )
                serialized = report.sections_to_dicts(sections)
                statuses = verify_sections(sections, texts)
                serialized_statuses = [
                    {
                        "index": st.index,
                        "uid": st.sentence.uid,
                        "status": st.status,
                        "reason": getattr(st, "reason", ""),
                        "is_factual": st.sentence.is_factual,
                        "source_ids": st.sentence.source_ids,
                    }
                    for st in statuses
                ]
                self._emit("gen_complete", {
                    "cancelled": False,
                    "sections": serialized,
                    "statuses": serialized_statuses,
                })
            except Exception as e:
                log.exception("Generation failed")
                self._emit("gen_error", {"error": str(e)})

        self._gen_thread = threading.Thread(target=run_thread, daemon=True)
        self._gen_thread.start()
        return {"started": True}

    def cancel_generation(self) -> dict[str, Any]:
        self._cancel_gen_event.set()
        return {"success": True}

    # =========================================================================
    # REVIEW & EDITING
    # =========================================================================

    def verify_document(self, sections_dicts: list[dict], sources_data: list[dict]) -> list[dict]:
        sections = report.sections_from_dicts(sections_dicts)
        texts = [s.get("text", "") for s in sources_data]
        statuses = verify_sections(sections, texts)
        return [
            {
                "index": st.index,
                "uid": st.sentence.uid,
                "status": st.status,
                "reason": getattr(st, "reason", ""),
                "is_factual": st.sentence.is_factual,
                "source_ids": st.sentence.source_ids,
            }
            for st in statuses
        ]

    def mark_non_factual_done(self, sections_dicts: list[dict], current_done: list[str]) -> dict[str, Any]:
        sections = report.sections_from_dicts(sections_dicts)
        done_set = set(current_done)
        for sec in sections:
            for p in sec.paragraphs:
                for s in p.sentences:
                    if not s.is_factual:
                        done_set.add(s.uid)
        return {"success": True, "done": list(done_set)}

    def paraphrase_sentence(self, sentence_dict: dict, sources_data: list[dict]) -> dict[str, Any]:
        sent = report.sentence_from_dict(sentence_dict)
        para = content.Paragraph([sent])
        sources = [record_to_source(s) for s in sources_data]
        texts = [s.get("text", "") for s in sources_data]
        cl = AIClient(self._cfg)
        try:
            new_para = content.paraphrase(para, sources, texts, cl)
            if new_para.sentences:
                new_sent = new_para.sentences[0]
                return {
                    "success": True,
                    "sentence": report.sentence_to_dict(new_sent),
                }
            return {"error": "Hasil parafrase kosong."}
        except Exception as e:
            return {"error": f"Gagal parafrase: {e}"}

    def request_dosen_review(self, sections_dicts: list[dict], sources_data: list[dict]) -> dict[str, Any]:
        sections = report.sections_from_dicts(sections_dicts)
        sources = [record_to_source(s) for s in sources_data]
        cited = {i for sec in sections for p in sec.paragraphs for s in p.sentences for i in s.source_ids}
        refs = report.references_for(sources, cited)
        cl = AIClient(self._cfg)
        try:
            notes = dosen.review_report(sections, refs, cl)
            return {
                "success": True,
                "notes": [asdict(n) for n in notes],
            }
        except Exception as e:
            return {"error": f"Gagal review dosen: {e}"}

    # =========================================================================
    # CITATION LABELS & BIBLIOGRAPHY
    # =========================================================================

    def compute_citations_and_references(
        self, sources_data: list[dict], sections_dicts: list[dict], style: str = "et_al"
    ) -> dict[str, Any]:
        sources = [record_to_source(s) for s in sources_data]
        sections = report.sections_from_dicts(sections_dicts)
        cited = {i for sec in sections for p in sec.paragraphs for s in p.sentences if s.citation for i in s.source_ids}
        labels = report.labels_for(sources, cited, style=style)
        label_forms = report.label_forms_for(sources, cited, style=style)
        refs = report.references_for(sources, cited)

        return {
            "labels": {str(k): v for k, v in labels.items()},
            "label_forms": {str(k): v for k, v in label_forms.items()},
            "references": refs,
            "cited_ids": list(cited),
        }

    # =========================================================================
    # PREFLIGHT & EXPORT
    # =========================================================================

    def run_preflight(self, state: dict[str, Any]) -> dict[str, Any]:
        sources_data = state.get("sources", [])
        sections_dicts = state.get("sections", [])
        done = set(state.get("done", []))
        fields = state.get("fields", {})

        sources = [record_to_source(s) for s in sources_data]
        texts = [s.get("text", "") for s in sources_data]
        sections = report.sections_from_dicts(sections_dicts)
        statuses = verify_sections(sections, texts)

        judul = fields.get("JUDUL", "Laporan")
        logo_path = Path(fields.get("LOGO_PATH")) if fields.get("LOGO_PATH") else None
        cited = {i for sec in sections for p in sec.paragraphs for s in p.sentences if s.citation for i in s.source_ids}
        style = self._cfg.citation_style
        done_set = frozenset(done)

        checks = preflight.run_checks(
            judul=judul,
            sources=sources,
            statuses=statuses,
            cited=cited,
            logo_path=logo_path,
            style=style,
            done=done_set,
        )
        issues = preflight.find_issues(
            judul=judul,
            sources=sources,
            statuses=statuses,
            cited=cited,
            logo_path=logo_path,
            style=style,
            done=done_set,
        )

        return {
            "checks": [asdict(c) for c in checks],
            "issues": [asdict(i) for i in issues],
            "can_export_directly": len(issues) == 0,
        }

    def export_report(self, state: dict[str, Any]) -> dict[str, Any]:
        sources_data = state.get("sources", [])
        sections_dicts = state.get("sections", [])
        fields = state.get("fields", {})
        template_id = state.get("template_id")
        open_word = state.get("open_word", True)
        style = state.get("style", self._cfg.citation_style)

        tpl_id_int: int | None = None
        if template_id is not None:
            try:
                tpl_id_int = int(template_id)
            except (ValueError, TypeError):
                tpl_id_int = None
        if tpl_id_int is None:
            return {"error": "Pilih template terlebih dahulu"}

        tpls = self.db.list_template()
        tpl = next((t for t in tpls if t.id == tpl_id_int), None)
        if not tpl or not Path(tpl.path).is_file():
            return {"error": "Template DOCX tidak ditemukan."}

        sources = [record_to_source(s) for s in sources_data]
        sections = report.sections_from_dicts(sections_dicts)
        cited = {i for sec in sections for p in sec.paragraphs for s in p.sentences if s.citation for i in s.source_ids}

        labels = report.labels_for(sources, cited, style=style)
        label_forms = report.label_forms_for(sources, cited, style=style)
        refs = report.references_for(sources, cited)

        judul = fields.get("JUDUL", "Laporan")
        filename = report.sanitize_filename(judul)
        paths.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = paths.OUTPUT_DIR / f"{filename}.docx"

        logo_path = fields.get("LOGO_PATH")
        if logo_path and not Path(logo_path).is_file():
            logo_path = None

        try:
            final_path = renderer.render_report(
                template_path=Path(tpl.path),
                fields=fields,
                sections=sections,
                references=refs,
                logo_path=Path(logo_path) if logo_path else None,
                output_path=out_path,
                labels=labels,
                update_fields=True,
                label_forms=label_forms,
            )
            # Simpan draf (jangan dihapus agar dapat dibuka & direvisi kembali)
            # drafts.delete_draft(DRAFT_ACTIVE_ID)

            if open_word and os.name == "nt":
                try:
                    os.startfile(str(final_path))
                except Exception:
                    pass

            return {"success": True, "output_path": str(final_path)}
        except Exception as e:
            log.exception("Export failed")
            return {"error": f"Gagal mengekspor laporan: {e}"}
