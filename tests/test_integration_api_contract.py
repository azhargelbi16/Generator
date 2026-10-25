"""Integration test verifying full compliance between ApiBridge and formal API Contract.

Slice arsitektur 5 menambah tiga lapis verifikasi:
1. Setiap endpoint contract = metode nyata di ApiBridge (lapis lama).
2. Setiap pemanggilan callApi di frontend/lib/api.ts menunjuk metode yang
   terdaftar di contract DAN ada di bridge, dengan JUMLAH ARGUMEN yang cocok
   dengan tanda tangan Python (arg order).
3. Amplop respons endpoint yang dulu salah terdokumentasi terkunci ke bentuk
   aktual (guard regresi bentuk lama).
"""

from pathlib import Path
import inspect
import re

from generator.web.api_bridge import ApiBridge
from generator.web.contract import API_VERSION, API_ENDPOINTS, get_contract_metadata
from generator import database

FRONTEND_API_TS = Path(__file__).resolve().parents[1] / "frontend" / "src" / "lib" / "api.ts"


def test_api_contract_metadata_integrity():
    meta = get_contract_metadata()
    assert meta["version"] == API_VERSION
    assert meta["total_endpoints"] == len(API_ENDPOINTS)
    assert len(API_ENDPOINTS) >= 45


def test_every_contract_endpoint_implemented_on_bridge(tmp_path: Path):
    db = database.Database(tmp_path / "test.db")
    db.init_schema()
    bridge = ApiBridge(db, config_path=tmp_path / "config.json")

    # Verify every endpoint in contract is a real callable method on ApiBridge
    for endpoint_name in API_ENDPOINTS:
        assert hasattr(bridge, endpoint_name), f"ApiBridge missing method '{endpoint_name}' defined in contract!"
        method = getattr(bridge, endpoint_name)
        assert callable(method), f"'{endpoint_name}' on ApiBridge is not callable!"

    db.close()


def test_every_public_bridge_method_documented_in_contract():
    """Metode publik bridge tidak boleh ada yang lolos dari kontrak; set_window
    adalah infrastruktur pywebview, bukan endpoint untuk frontend."""
    documented_exceptions = {"set_window"}
    methods = {
        n for n, m in vars(ApiBridge).items()
        if callable(m) and not n.startswith("_")
    }
    undocumented = sorted(methods - set(API_ENDPOINTS) - documented_exceptions)
    assert undocumented == [], f"Metode bridge belum terdaftar di contract.py: {undocumented}"


# --- Lapis 2: nama metode & urutan argumen api.ts vs Python ------------------

_CALL_RE = re.compile(r"callApi<[^>]*>\(\s*'([a-z_]+)'\s*(,|\))", re.S)


def _split_top_level_args(text: str) -> list[str]:
    """Pecah daftar argumen pada koma tingkat teratas (koma di dalam kurung,
    kurawal, atau string sederhana tidak memecah)."""
    args: list[str] = []
    depth = 0
    current: list[str] = []
    in_string: str | None = None
    for ch in text:
        if in_string:
            current.append(ch)
            if ch == in_string:
                in_string = None
            continue
        if ch in "'\"":
            in_string = ch
            current.append(ch)
            continue
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            args.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    tail = "".join(current).strip()
    if tail:
        args.append(tail)
    return args


def _frontend_calls() -> list[tuple[str, int]]:
    """Semua (nama_metode, jumlah_argumen) panggilan callApi di api.ts."""
    source = FRONTEND_API_TS.read_text(encoding="utf-8")
    calls: list[tuple[str, int]] = []
    for header in re.finditer(r"callApi<[^>]*>\(", source):
        open_paren = header.end() - 1
        depth = 0
        end = open_paren
        for i in range(open_paren, len(source)):
            if source[i] in "([{":
                depth += 1
            elif source[i] in ")]}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        inner = source[open_paren + 1 : end]
        method_match = re.match(r"\s*'([a-z_]+)'\s*(?:,|$)", inner)
        if not method_match:
            continue
        method = method_match.group(1)
        rest = inner[method_match.end():]
        args = _split_top_level_args(rest) if rest.strip() else []
        calls.append((method, len(args)))
    return calls


def _python_signature(name: str) -> tuple[int, int]:
    """(jumlah param total, jumlah param wajib) dari metode bridge."""
    params = inspect.signature(getattr(ApiBridge, name)).parameters.values()
    total = 0
    required = 0
    for p in params:
        if p.name in ("self", "args", "kwargs"):
            continue
        total += 1
        if p.default is inspect.Parameter.empty:
            required += 1
    return total, required


def test_frontend_calls_point_to_contracted_bridge_methods():
    calls = _frontend_calls()
    assert len(calls) >= 40, "Pemindai callApi gagal membaca api.ts"
    for method, _ in calls:
        assert method in API_ENDPOINTS, (
            f"api.ts memanggil '{method}' yang tidak terdaftar di contract.py"
        )
        assert hasattr(ApiBridge, method), (
            f"api.ts memanggil '{method}' yang tidak ada di ApiBridge"
        )


def test_frontend_call_argument_counts_match_python_signatures():
    for method, js_arg_count in _frontend_calls():
        total, required = _python_signature(method)
        assert js_arg_count <= total, (
            f"{method}: frontend mengirim {js_arg_count} argumen, "
            f"Python hanya menerima {total}"
        )
        assert js_arg_count >= required, (
            f"{method}: frontend mengirim {js_arg_count} argumen, "
            f"Python mewajibkan {required}"
        )


# --- Lapis 3: kunci amplop respons terkunci ke bentuk aktual -----------------

# Guard regresi: bentuk-bentuk lama yang pernah salah terdokumentasi
# (source vs record, statuses map vs array, started vs success, dst.).
_ACTUAL_ENVELOPE_KEYS = {
    "start_generation": ["started", "error"],
    "add_manual_source": ["record"],
    "pick_pdf_source": ["record"],
    "add_web_source": ["record"],
    "resolve_doi_source": ["record"],
    "load_active_draft": ["has_draft"],
    "run_preflight": ["checks", "issues", "can_export_directly"],
    "compute_citations_and_references": ["labels", "label_forms", "references", "cited_ids"],
    "get_document_analytics": ["DocumentAnalytics"],
    "mark_non_factual_done": ["done"],
    "get_reviewed_snapshot": ["statuses", "citations", "analytics"],
}

_FORBIDDEN_STALE_KEYS = {
    "add_manual_source": ["source?: SourceRecord"],
    "start_generation": ["success: boolean, error?: string"],
    "verify_document": ["statuses: Record"],
    "run_preflight": ["passed: boolean"],
    "load_active_draft": ["DraftState | null"],
}


def test_contract_documents_actual_response_envelopes():
    for endpoint, keys in _ACTUAL_ENVELOPE_KEYS.items():
        assert endpoint in API_ENDPOINTS, f"{endpoint} belum ada di contract.py"
        returns = API_ENDPOINTS[endpoint]["returns"]
        for key in keys:
            assert key in returns, (
                f"contract.py '{endpoint}' tidak lagi mendokumentasikan "
                f"kunci aktual '{key}' (bentuk berubah?)"
            )


def test_contract_does_not_regress_to_stale_shapes():
    for endpoint, stale in _FORBIDDEN_STALE_KEYS.items():
        returns = API_ENDPOINTS[endpoint]["returns"]
        for fragment in stale:
            assert fragment not in returns, (
                f"contract.py '{endpoint}' kembali memakai bentuk lama: '{fragment}'"
            )


def test_frontend_ts_contract_matches_python_endpoint_list():
    """api-contract.ts harus mendeklarasikan metode yang sama dengan
    contract.py — kontrak TS adalah sumber tipe untuk seluruh api.ts."""
    ts_source = (FRONTEND_API_TS.parent / "api-contract.ts").read_text(encoding="utf-8")
    not_in_ts = [
        e for e in API_ENDPOINTS
        if f"{e}(" not in ts_source
    ]
    assert not_in_ts == [], f"api-contract.ts kehilangan deklarasi: {not_in_ts}"


def test_bridge_versioning_endpoints(tmp_path: Path):
    db = database.Database(tmp_path / "test.db")
    db.init_schema()
    bridge = ApiBridge(db, config_path=tmp_path / "config.json")

    assert bridge.get_api_version() == API_VERSION
    contract = bridge.get_api_contract()
    assert contract["version"] == API_VERSION
    assert "endpoints" in contract

    db.close()


def test_bridge_error_handling_contract_compliance(tmp_path: Path):
    db = database.Database(tmp_path / "test.db")
    db.init_schema()
    bridge = ApiBridge(db, config_path=tmp_path / "config.json")

    # 1. Invalid DOI should return failure envelope, not raise uncaught exception
    res_doi = bridge.resolve_doi_source("invalid/not-a-real-doi-12345")
    assert isinstance(res_doi, dict)
    assert res_doi["success"] is False
    assert "error" in res_doi

    # 2. Invalid Web URL should return failure envelope
    res_web = bridge.add_web_source("https://invalid-non-existent-domain-9999.org/paper")
    assert isinstance(res_web, dict)
    assert res_web["success"] is False
    assert "error" in res_web

    # 3. Invalid Named Draft state should return failure envelope
    res_draft = bridge.save_named_draft("test_draft", "invalid-non-dict-payload")
    assert isinstance(res_draft, dict)
    assert res_draft["success"] is False
    assert "error" in res_draft

    db.close()
