# Handoff: architecture deepening for Generator Laporan

## Goal

Execute the architecture improvements identified in the review report. Preserve
the current user-facing behavior and saved draft format while making the main
modules deeper, easier to test through their interfaces, and easier to navigate.

The requested scope is all five candidates, in this order:

1. Active-draft reconciliation.
2. Reviewed-document state.
3. Report-generation orchestration.
4. SourceRecord intake and metadata policy.
5. Frontend-to-Python interface alignment.

Do not commit or push unless the user explicitly asks.

## Current state

- Repository: `C:\Generator`
- Branch: `master`
- Current revision: `06da785`
- Working tree: clean after cancelling and reverting an incomplete refactor.
- Existing architecture report: `C:\Users\ACER\AppData\Local\Temp\architecture-review-20261025-071704.html`
- No `GLOSSARY.md` exists.
- No `docs/adr/` directory exists.
- Domain vocabulary is documented in `README.md`, `DOKUMENTASI_WORKFLOW.md`, and
  `docs/handoff/BRIEF_ANTIGRAVITY.md`.

The previous agent briefly attempted a partial refactor, then fully restored all
tracked files and deleted its new files. No incomplete implementation remains.

## Main findings

### 1. Active-draft reconciliation, Strong

Relevant files:

- `src/generator/web/api_bridge.py`, especially `save_active_draft`
- `src/generator/drafts.py`
- `frontend/src/components/TabLaporan.tsx`
- `frontend/src/components/TabReview.tsx`
- `tests/test_regression_uat.py`

The report tab owns fields and sources. The review tab owns sections and done
marks. Their partial payloads rely on `ApiBridge.save_active_draft()` to infer
whether omitted or empty values mean preserve or clear. This is the highest
priority seam because the regression tests already demonstrate the preservation
rules.

Recommended implementation:

- Move merge, preserve, clear, and archive decisions into a public operation in
  `drafts.py`.
- Keep `ApiBridge.save_active_draft()` as a thin adapter.
- Preserve the existing JSON draft format and the current behavior of
  `clear_sections`.
- Add behavior tests for review payloads, report payloads, empty new drafts, and
  explicit source clearing.

### 2. Reviewed-document state, Strong

Relevant files:

- `frontend/src/components/TabReview.tsx`
- `frontend/src/App.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/api-contract.ts`
- `src/generator/web/api_bridge.py`
- `src/generator/report.py`
- `src/generator/preflight.py`
- `tests/test_analytics.py`
- `tests/test_integration_fixtures.py`

Normalization, verification, citation calculation, analytics, preflight, and
export preparation repeatedly reconstruct the same sections and sentences.

Recommended implementation:

- Add a backend reviewed-document module that owns normalized sections, source
  texts, sentence statuses, cited IDs, citation payloads, and analytics.
- Add one snapshot operation for the screen and sidebar to use.
- Keep existing operations available for compatibility, but make them delegate
  to the reviewed-document implementation.
- Move `normalizeReviewSections` out of `TabReview.tsx` into a frontend library
  module.
- Preserve the current status names and response envelopes used by the UI.

### 3. Report-generation orchestration, Strong

Relevant files:

- `src/generator/ai/content.py`
- `src/generator/web/api_bridge.py`
- `frontend/src/components/TabLaporan.tsx`
- `tests/test_content.py`
- `tests/test_e2e_pipeline.py`

The variant and ordinary batch paths duplicate streaming, cancellation, JSON
repair, partial recovery, progress, and merging policy.

Recommended implementation:

- Extract the shared generation step from `content.py` into a private
  implementation helper.
- Keep the public `generate_sections` behavior unchanged.
- Keep `GenerationProgress` as the seam used by the browser event adapter.
- Add or strengthen tests for both generation paths, event ordering, partial
  output, and cancellation.

### 4. SourceRecord intake, Worth exploring

Relevant files:

- `src/generator/web/api_bridge.py`
- `src/generator/sources/records.py`
- `src/generator/sources/pdf_reader.py`
- `src/generator/sources/web_reader.py`
- `src/generator/sources/doi_resolver.py`
- `frontend/src/components/TabLaporan.tsx`
- `tests/test_web_api_bridge.py`

PDF, web, manual, and DOI entry points repeat metadata precedence, fallback
titles, enrichment, and identity decisions.

Recommended implementation:

- Add a source-intake module that converts DOI metadata consistently, merges
  metadata, selects fallback titles, and produces `SourceRecord` values.
- Keep PDF, web, manual, and DOI readers as adapters.
- Preserve the `source_metadata_ready` event and its `ref` matching behavior.
- Add success-path parity tests for all source kinds.

### 5. Frontend-to-Python interface alignment, Speculative until the above settle

Relevant files:

- `frontend/src/lib/api-contract.ts`
- `frontend/src/lib/api.ts`
- `src/generator/web/contract.py`
- `src/generator/web/api_bridge.py`
- `tests/test_integration_api_contract.py`

The declared interface disagrees with runtime calls in several places. Examples
include `start_generation`, `verify_document`, `add_manual_source`, draft
loading, preflight response shapes, and DOI response shapes. The frontend bridge
also uses a generic method lookup that weakens type checking.

Recommended implementation:

- First document the actual Python method signatures and response envelopes.
- Align TypeScript and Python metadata to those actual shapes.
- Remove or narrow the generic method escape hatch in `api.ts` only after the
  runtime shapes are stable.
- Add tests that compare method names, argument order, and key response fields.

## Constraints and compatibility

- Keep the existing React, TypeScript, pywebview, and Python stack.
- Do not add dependencies.
- Do not change the SQLite schema.
- Keep old draft JSON files readable.
- Do not expose API keys in responses, logs, tests, or commits.
- Keep Indonesian UI text and current status labels.
- Do not delete tests or weaken export verification.
- Avoid editing `data/`, `output/`, `.venv/`, or live draft files.

## Baseline checks already run

The following checks passed before the cancelled refactor:

```text
python -m pytest -q
293 passed in 27.93s
```

```text
cd frontend
npm run build
vite build succeeded
```

The cancelled refactor also ran a focused draft test command successfully, but
those changes were reverted:

```text
python -m pytest -q tests/test_drafts.py tests/test_regression_uat.py
18 passed in 2.45s
```

## Next step

Start with a fresh baseline check, then implement only the first vertical slice:

```powershell
python -m pytest -q tests/test_drafts.py tests/test_regression_uat.py
```

Add the active-draft reconciliation operation and its behavior tests, make
`ApiBridge.save_active_draft()` delegate to it, and rerun the focused tests
before moving to reviewed-document state.

## Handoff prompt

You are continuing work in `C:\Generator` on the architecture deepening plan in
this file. The working tree is clean at commit `06da785`. Implement the five
candidates in order, preserving behavior and saved formats. Begin with active
draft reconciliation. Read the affected callers and tests before editing. Work
in vertical slices, run focused tests after each slice, then run `python -m
pytest -q` and `cd frontend; npm run build` at the end. Do not commit unless the
user asks.
