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
from ..sources import pdf_reader, web_reader
from ..sources.records import (
    DRAFT_ACTIVE_ID,
    normalize_metadata,
    record_to_source,
    source_to_record,
)
from ..verification import verify_sections, STATUS_VERIFIED, STATUS_UNVERIFIED, STATUS_NON_FACTUAL

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
        return asdict(self._cfg)

    def save_config(self, cfg_data: dict[str, Any]) -> dict[str, Any]:
        try:
            temp = float(str(cfg_data.get("ai_temperature", 0.2)).replace(",", "."))
            temp = max(0.0, min(2.0, temp))
        except (ValueError, TypeError):
            temp = 0.2

        self._cfg = config.Config(
            ai_base_url=str(cfg_data.get("ai_base_url", "http://localhost:1234/v1")).strip(),
            ai_api_key=str(cfg_data.get("ai_api_key", "")).strip(),
            ai_model=str(cfg_data.get("ai_model", "gpt-4o-mini")).strip(),
            ai_temperature=temp,
            citation_style=str(cfg_data.get("citation_style", "et_al")),
            dosen_review=bool(cfg_data.get("dosen_review", False)),
        )
        config.save_config(self._cfg, self.config_path)
        return {"success": True, "config": asdict(self._cfg)}

    def test_ai_connection(self, base_url: str | None = None, api_key: str | None = None, model: str | None = None) -> dict[str, Any]:
        test_cfg = self._cfg
        if base_url:
            test_cfg = config.Config(
                ai_base_url=str(base_url).strip(),
                ai_api_key=str(api_key if api_key is not None else self._cfg.ai_api_key).strip(),
                ai_model=str(model if model is not None else self._cfg.ai_model).strip(),
                ai_temperature=self._cfg.ai_temperature,
                citation_style=self._cfg.citation_style,
                dosen_review=self._cfg.dosen_review,
            )
        cl = AIClient(test_cfg)
        ok, msg = client.check_connection(cl)
        return {"ok": ok, "message": msg}

    def fetch_models(self, base_url: str | None = None, api_key: str | None = None) -> dict[str, Any]:
        test_cfg = self._cfg
        if base_url:
            test_cfg = config.Config(
                ai_base_url=str(base_url).strip(),
                ai_api_key=str(api_key if api_key is not None else self._cfg.ai_api_key).strip(),
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

    def _ensure_default_template(self) -> None:
        try:
            paths.TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
            dest_path = paths.TEMPLATES_DIR / "Template_Standar_Akademik.docx"
            if not dest_path.is_file():
                from docx import Document
                from docx.shared import Cm, Pt
                doc = Document()

                p_judul = doc.add_paragraph()
                p_judul.paragraph_format.space_before = Cm(2)
                p_judul.paragraph_format.space_after = Cm(1.5)
                r_judul = p_judul.add_run("{{JUDUL}}")
                r_judul.bold = True
                r_judul.font.size = Pt(16)
                p_judul.alignment = 1

                p_logo = doc.add_paragraph("{{LOGO}}")
                p_logo.alignment = 1
                p_logo.paragraph_format.space_after = Cm(2)

                p_meta = doc.add_paragraph()
                p_meta.alignment = 1
                p_meta.add_run("Disusun Oleh:\n").bold = True
                p_meta.add_run("Nama: {{NAMA}}\nNIM: {{NIM}}\n\n")
                p_meta.add_run("Dosen Pembimbing:\n").bold = True
                p_meta.add_run("{{DOSEN}}\n\n")
                p_meta.add_run("Mata Kuliah: {{MATA_KULIAH}}\n")
                p_meta.add_run("{{TANGGAL}}")
                doc.add_page_break()

                h_toc = doc.add_paragraph()
                r_toc = h_toc.add_run("DAFTAR ISI")
                r_toc.bold = True
                r_toc.font.size = Pt(14)
                h_toc.alignment = 1
                doc.add_paragraph("{{DAFTAR_ISI}}")
                doc.add_page_break()

                doc.add_paragraph("{{ISI_LAPORAN}}")
                doc.add_page_break()

                h_pus = doc.add_paragraph()
                r_pus = h_pus.add_run("DAFTAR PUSTAKA")
                r_pus.bold = True
                r_pus.font.size = Pt(14)
                h_pus.alignment = 1
                doc.add_paragraph("{{DAFTAR_PUSTAKA}}")

                doc.save(dest_path)

            all_tpls = self.db.list_template()
            if not any(Path(t.path).resolve() == dest_path.resolve() for t in all_tpls):
                self.db.add_template(database.Template(
                    0,
                    "Template Standar Akademik",
                    "Template Word resmi lengkap cover, logo, TOC, dan daftar pustaka",
                    str(dest_path)
                ))
        except Exception as e:
            log.warning(f"Gagal memastikan template default: {e}")

    def create_default_template(self) -> dict[str, Any]:
        self._ensure_default_template()
        return {"success": True}

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
        val_result = template.validate_template(dest_path)
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
        except AIError:
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
        except AIError:
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
        except AIError:
            source = Source([], "", "Teks Manual")

        merged = bibliography.merge_metadata(source, {})
        record = source_to_record(merged, text, "manual")
        return {"success": True, "record": record}

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
                "is_factual": st.sentence.is_factual,
                "source_ids": st.sentence.source_ids,
            }
            for st in statuses
        ]

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

        tpls = self.db.list_template()
        tpl = next((t for t in tpls if t.id == int(template_id)), None)
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
            # Remove active draft on successful export
            drafts.delete_draft(DRAFT_ACTIVE_ID)

            if open_word and os.name == "nt":
                try:
                    os.startfile(str(final_path))
                except Exception:
                    pass

            return {"success": True, "output_path": str(final_path)}
        except Exception as e:
            log.exception("Export failed")
            return {"error": f"Gagal mengekspor laporan: {e}"}
