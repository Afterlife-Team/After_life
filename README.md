[README_content_preservation (1).md](https://github.com/user-attachments/files/34223815/README_content_preservation.1.md)
# 🕸️ 404 Afterlife — Content Preservation & Full-Site Recovery

**Dead websites, reborn — preserve the real pages, content, links, and assets.**

> **Branch:** `feature/content-preservation`  
> **Repository:** [Afterlife-Team/After_life](https://github.com/Afterlife-Team/After_life)  
> **Challenge:** Hacktoberfest 2026 — Ghost in the Machine

## About this branch

This branch focuses on **preserving existing website content while recovering and modernizing static websites**. It combines the team's original website-analysis work with a separate, integrated full-site Streamlit implementation under `full_site/`.

Rather than generating a visually attractive replacement that silently drops original information, the workflow starts with the available website files, inspects their structure, applies a selected modernization method, and compares the resulting files against the originals.

**Important distinction:** The built-in **Safe CSS refresh is deterministic, not AI-generated**. AI-assisted changes are supported through a team endpoint or imported JSON; whether an actual model is used depends on the selected integration and its configuration. This branch does not bundle a trained model or model weights.

## What this branch provides

- **ZIP ingestion:** accepts a bundle of static website files, validates entries, and keeps supported HTML, CSS, images, fonts, scripts, and related assets.
- **Website analysis:** inspects available HTML pages, headings, paragraphs, links, images, CSS colors, and missing local references.
- **Content-preserving modernization:** applies a shared CSS refresh across the included HTML pages without presenting the result as AI-generated.
- **Wayback recovery:** attempts to retrieve a bounded set of archived pages and assets from Internet Archive snapshots, with a coverage report.
- **Before/after comparison:** previews the same selected page from the original and redesigned bundles.
- **AI integration contract:** exports original HTML/CSS and asset metadata for the AI team; accepts validated HTML/CSS updates through JSON or a configured endpoint.
- **Downloads:** exports the accepted original bundle, redesigned ZIP, AI input JSON, and recovery report when applicable.
- **Testing:** includes automated tests for parsing, preservation, security constraints, mocked archive behavior, integration, and the Streamlit entry point.

## Repository layout

```text
After_life/
├── README.md                    # Branch-level documentation
├── analyzer.py                  # Original team website analyzer
├── tests/test_analyzer.py       # Original analyzer tests
├── sample_site/                 # Original team samples
├── app.py                       # Earlier UI; not the runnable full-site entry point
├── pytest.ini                   # Test discovery/configuration
└── full_site/
    ├── app.py                   # Runnable full-site Streamlit application
    ├── requirements.txt         # Full-site dependencies
    ├── RUN_WINDOWS.bat          # Windows launcher
    ├── examples/
    │   └── sample_website_404_afterlife.zip
    ├── services/
    │   ├── site_bundle.py       # ZIP reading, validation, export
    │   ├── analysis.py          # Whole-site static analysis
    │   ├── preview.py           # Restricted static page preview
    │   ├── redesign.py          # Deterministic CSS modernization
    │   ├── archive_site.py      # Wayback retrieval and coverage
    │   ├── security.py          # URL safety checks
    │   ├── ai_bridge.py         # AI JSON/endpoint integration
    │   └── ...                  # Other support/compatibility modules
    └── tests/                   # Full-site and integration tests
```

The root-level `app.py` is a legacy interface with unresolved imports in this branch. **Run `full_site/app.py` instead.** Existing teammate files were preserved rather than overwritten when the full-site implementation was incorporated.

## How the pipeline works

```text
Upload website ZIP                 Enter website URL
        |                                 |
        v                                 v
 Validate and read files       Select Wayback capture
        |                         Recover available files
        +----------------+----------------+
                         |
                         v
                Analyze original site
                         |
                         v
                 Choose redesign path
                   /     |       \
             CSS refresh |     Team AI endpoint
                         |     or imported AI JSON
                         v
              Validate / assemble output
                         |
                         v
                Analyze redesigned site
                         |
                         v
          Compare pages and download ZIP
```

### Preservation approach

The system operates on the **available static files**, not on an imagined reconstruction of an entire historical website. It attempts to keep existing text, local references, and asset bytes. Its checks are conservative and heuristic; they are **not a proof** that every visual, functional, or semantic detail remains unchanged.

### Archive coverage

Archive recovery is deliberately bounded. The current documented limits are up to **12 pages, 60 assets, 20 MiB total**, and **3 MiB per resource**, subject to what the Internet Archive actually has. The recovery report separates discovered, recovered, failed, and unattempted items. Missing historical content cannot be guaranteed to be restored.

Internet Archive rate limits may cause HTTP 429 errors. Successful responses can be cached, but there is no independent archive provider fallback in this branch.

## Installation (Windows PowerShell)

**Requirements:** Python 3.11 or newer, pip, and an internet connection for the initial installation. Internet access is also needed for live Wayback retrieval or remote AI services.

From the repository root:

```powershell
git clone https://github.com/Afterlife-Team/After_life.git
cd After_life
git switch feature/content-preservation

python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r full_site\requirements.txt
cd full_site
..\.venv\Scripts\python.exe -m streamlit run app.py
```

Alternatively, launch `full_site/RUN_WINDOWS.bat` on Windows; it prepares its own environment under `full_site/`.

**Note:** ZIP input + Safe CSS refresh can work offline after dependencies have been installed. Wayback recovery and a remote AI endpoint require network access.

## Quick demo

1. Start the Streamlit application from `full_site/`.
2. Choose **Upload ZIP**.
3. Upload `full_site/examples/sample_website_404_afterlife.zip`.
4. Select **Safe CSS refresh (works now)**.
5. Click **Revive Entire Website**.
6. Inspect the analysis and select matching pages in **Before / After**.
7. Download the redesigned website ZIP and compare its files with the accepted original bundle.

You can also select **Recover from URL**, supply a public HTTP(S) address, and optionally choose an archive year. Success depends on Internet Archive availability and coverage.

## Optional AI integration

The full-site workflow exposes an integration contract for the team's AI reconstruction component. This allows the content-preservation layer to remain separate from model execution.

**Option A — Import AI JSON:** export the AI input JSON from the application, process it with the team's model/service, and import a response containing updated existing HTML/CSS files.

**Option B — Trusted endpoint:** configure the endpoint before starting Streamlit:

```powershell
$env:AFTERLIFE_AI_ENDPOINT = "http://127.0.0.1:8000/redesign"
# Only when the service requires a token:
$env:AFTERLIFE_AI_API_KEY = "your-secret-token"
```

Example response shape:

```json
{
  "files": {
    "index.html": "<html>...complete revised original page...</html>"
  }
}
```

The validator checks for unexpected file paths, certain missing references, script/event-handler changes, and detectable text loss. It cannot guarantee perfect preservation or prove that an imported JSON response was AI-generated. A separate local Gemma/Ollama workflow may exist in other versions of the project; **do not assume this branch's endpoint is running Gemma without checking the connected service**.

## Tests and verification

From the repository root after installing dependencies:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest_tmp
.\.venv\Scripts\python.exe -m compileall -q full_site analyzer.py
```

**Recorded verification (October 29, 2026):** the branch documentation reports **42 passing pytest tests** on Windows with Python 3.15.2, along with successful syntax compilation and a basic Streamlit health check. These are historical results from that verification run, **not a claim that the latest commit was retested for this README**.

The tests cover original analyzer behavior, ZIP handling, link/reference checks, preservation, SVG restrictions, AI response validation, mocked Wayback/rate limits, an HTTP AI stub, and basic UI smoke checks. Full live archive crawling, real model quality, and visual browser fidelity were not established by that test run.

## Security and limitations

- Only upload websites you own or have permission to process.
- ZIP files are subject to size, file-count, path, duplicate-name, and file-type restrictions; unsupported entries may be omitted.
- Static analysis does not verify the availability of external links.
- Archive recovery does not reconstruct server-side PHP/ASP behavior, databases, login flows, or content missing from the archive.
- The preview disables scripts and form submissions, sanitizes SVG, and blocks remote resources; it is **not** a production-grade sandbox.
- Original JavaScript files may remain in exported bundles. Review all exports before deploying them publicly.
- Do not commit environments, API keys, secrets, private uploaded sites, generated exports, or archive caches.

## Branch ownership and team context

**Branch:** `feature/content-preservation`  
**Branch implementation and ownership:** **Sozan (سوزان)**

Sozan developed the content-preservation work documented in this branch, including the full-site preservation and recovery workflow described above. This branch should be credited to **Sozan**, not Rana.

404 Afterlife is a collaborative team project with **Sozan, Rana, and Malak**. Their contributions elsewhere in the project are separate from authorship of this branch. Git commits and pull requests provide the detailed change history.

## Project status

This is a **hackathon prototype**, not a production website-restoration service. The branch demonstrates static content analysis, bounded archival recovery, deterministic modernization, comparison, export, and a contract for AI-assisted updates. Further work includes stronger browser-based regression tests, improved historical coverage, better visual preservation evaluation, and production isolation for untrusted website content.

---

**404 Afterlife** · Hacktoberfest 2026 · *Preserve what the web remembers; be explicit about what it does not.*
