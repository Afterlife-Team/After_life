# 404 Afterlife

Recover and modernize real static websites while preserving their pages and assets. The runnable full-site application lives in **`full_site/`**. Its CSS refresh works offline with a ZIP; actual AI redesign requires the team's service or imported JSON.

## Repository layout and team compatibility

- `full_site/app.py`: complete Streamlit workflow, ZIP/Wayback ingestion, page comparison, analysis, AI JSON exchange and downloads.
- `full_site/services/`: ingestion, analysis, preview, deterministic redesign, archive recovery and AI validation.
- `full_site/tests/`: full-site, security, mocked Wayback, HTTP integration and Streamlit smoke tests.
- `full_site/examples/sample_website_404_afterlife.zip`: sample static site.
- `analyzer.py`, `tests/test_analyzer.py`, `sample_site/` and root demo scripts: original team analyzer, preserved.
- Root `app.py`: preserved earlier UI. It imports absent `services.analyzer`/`services.ai_redesign` and is **not the runnable entry point**. Use `full_site/app.py`.

The full-site implementation was imported into a separate directory from the local project package. Alternate `*_rec*`/numbered backup modules, generated example outputs, environments, archive caches and local reports were not imported. No existing teammate Python files were replaced. Legacy `full_site/services/archive.py` and `reconstruct.py` remain for compatibility; the new UI uses `archive_site.py` and `redesign.py`.

## Current functionality

1. **ZIP input:** accepts up to 15 MiB compressed, 350 entries, 7 MiB per supported file and 45 MiB of supported uncompressed data. Rejects unsafe paths, duplicate names (case insensitive), encrypted entries and Unix symlinks/special files. Unsupported extensions are omitted with a warning. Reads `.html` and `.htm`, CSS, images, fonts, JavaScript and supported static assets without extracting or executing them.
2. **Analysis:** analyzes every included HTML page, headings, paragraphs, links, images, CSS colors and missing local references. This is static analysis, not a browser rendering or external-link availability check.
3. **CSS refresh:** adds a shared stylesheet to every page, with a conservative mode for complex sites. Simple secondary pages may receive homepage-derived navigation; unavailable responsive image candidates are removed and protocol-relative navigation links gain HTTPS. Original asset bytes are retained. This mode is **not AI**.
4. **Before/After:** select the same page in both views. Local styles/images/fonts are inlined, SVG is sanitized, scripts and form submission are blocked, and a restrictive CSP blocks remote resource loads. External navigation links can open a new tab; use the page selector for internal navigation.
5. **Downloads:** original accepted bundle, redesigned website ZIP, AI input JSON, and Wayback recovery report where applicable. The original bundle download contains accepted files, not a byte-for-byte copy of the uploaded ZIP.

## Wayback URL recovery

URL recovery remains available alongside ZIP input. It validates public HTTP(S) URLs, queries the Internet Archive Availability API, and can fall back to CDX for a requested year. A chosen year must match the returned capture; automatic mode asks for an available closest capture.

The crawler attempts up to **12 pages / 60 assets / 20 MiB**, with a 3 MiB resource limit, on the same host. It follows only approved Archive API/replay redirects, downloads available HTML/CSS/images/fonts, rewrites recovered references and reports discovered, attempted, recovered, failed and unattempted resources. These counts do not establish completeness of the historical site. Off-host assets, JS-driven content and backend services are outside this recovery.

Successful responses are cached locally in `full_site/.cache/wayback.sqlite3` (availability/CDX about 1 hour, replay resources 7 days; body budget 64 MiB). HTTP 429 honors Retry-After or a default 5-minute cooldown; cached successes remain usable. It does not immediately retry CDX after a 429. Both API paths still depend on Internet Archive: there is **no independent archive-provider fallback**. If unavailable, wait or upload a ZIP; repeated Revive clicks will not recover unarchived material.

## Install and run — Windows PowerShell

Use Python 3.11 or newer. Run these commands from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r full_site\requirements.txt
cd full_site
..\.venv\Scripts\python.exe -m streamlit run app.py
```

Alternatively, double-click `full_site/RUN_WINDOWS.bat`; it creates its own environment inside `full_site/`, installs requirements and launches the app. Network access is needed for initial dependency installation, Wayback and a remote AI endpoint. ZIP + CSS refresh runs offline after installation.

Demo: Upload ZIP → choose `sample_website_404_afterlife.zip` → Safe CSS refresh → Revive Entire Website → compare the available pages → download the redesigned ZIP.

## Team AI integration

No Gemma/model runtime or provider credentials are bundled. Two integration routes are implemented:

- Export the original HTML/CSS and asset manifest as JSON, obtain revised files from the AI team, then select **Import team AI JSON**.
- Configure a trusted JSON HTTP endpoint before starting Streamlit:

```powershell
$env:AFTERLIFE_AI_ENDPOINT = "http://127.0.0.1:8000/redesign"
# Only if required by the team service:
$env:AFTERLIFE_AI_API_KEY = "your-secret-token"
```

Remote endpoints require HTTPS; local HTTP supports localhost/127.0.0.1. The endpoint receives a POST containing `task`, `homepage`, `files`, `assets` and preservation rules. HTML/CSS request text is capped at 1.2 MB; HTTP connect/read timeouts are 5/120 seconds. The response body is checked against 3 MB after receipt (not streamed), with a 1.5 MB per-file edit limit.

Expected response:

```json
{"files": {"index.html": "<html>...complete revised original page...</html>"}}
```

Return **every original HTML page**, plus optional existing CSS files. Validation rejects unknown paths, dropped anchor/image references, changed script tags/event handlers, and detected text loss; original binary assets remain. Validation is heuristic, does not verify AI provenance, and does not fully enforce all prompt rules (such as no new forms/external dependencies in HTML). Review output before deployment. See [the full AI contract](full_site/TEAM_AI_INTERFACE.md).

## Tests and verification

From the repository root after installation:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest_tmp
.\.venv\Scripts\python.exe -m compileall -q full_site analyzer.py
```

`pytest.ini` selects the actual test directories and makes `full_site/services` importable. Root `test_run.py`, `test_links.py` and `test_zip.py` are standalone demos, not pytest test cases; `test_zip.py` writes `analysis_result.json`, so it is excluded from automatic collection.

Verification on **2026-10-29**, Windows, Python 3.15.2: **42 pytest tests passed**, covering the original analyzer, ZIP preservation/export, reference resolution, text preservation, SVG restrictions, AI validation, a real local HTTP AI stub, mocked archive fallback/rate limits/coverage, and Streamlit initial rendering/input errors. Syntax compilation passed. A temporary headless Streamlit server returned **200 / ok** on `/_stcore/health` and was stopped. A single live Availability API request returned **200** and an available example.com capture. Full live archive crawling and an actual team model were not exercised; their success is not implied by these checks. No fresh dependency installation or visual browser review was performed.

Fixes made in the imported implementation: exclude `<head>` from visible-text comparison; reject changed short text; validate raw ZIP member names before Windows normalizes separators; handle prohibited SVG entities without crashing the preview. ZIP fixtures retain raw backslashes so the Windows regression test exercises the actual rejection path.

## Limitations and local data

This is a hackathon prototype for static sites. It cannot restore databases, PHP/ASP server behavior or assets absent from an archive/ZIP. Preview deliberately differs from a live site because JavaScript is disabled. Original JS remains in exported ZIPs. Meta CSP and Streamlit iframes are not a hardened production sandbox; public hosting needs isolated origins, HTTP security headers and network isolation. CSS and preservation checks are conservative heuristics and need manual review.

Do not commit `.venv/`, `.cache/`, `.pytest_cache/`, `.pytest_tmp*/`, `.env*`, Streamlit secrets, API tokens, user uploads or generated private website exports. The existing root `analysis_result.json` is a previously tracked sample result; this change does not regenerate it. Dependencies are version-ranged, not locked; the verified runtime used Streamlit 1.66.1, pytest 9.2.0, requests 2.34.2, BeautifulSoup 4.15.0 and defusedxml 0.7.1.
