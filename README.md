# 🕸️ 404 Afterlife

### Dead websites, reborn — preserving real pages, content, and assets.

**Hacktoberfest 2026 · Ghost in the Machine · Feature/UI — Malak's first submitted version**

404 Afterlife is a **Streamlit-based website recovery and modernization prototype**. Users can upload an existing static website as a ZIP file or recover an archived snapshot from the Internet Archive, inspect the site's content and missing references, compare pages **before and after** modernization, and export the reconstructed website.

This README documents the **actual files in the first `feature/ui` ZIP submission**, including the runnable application in `full_site/`. It is not documentation for the older, single-page baseline alone.

> **What is AI here?** The built-in **Safe CSS refresh is deterministic, not AI**. The interface also supports a **team AI endpoint** or **imported AI JSON**, but it does not bundle a language model or prove that an AI service ran. The distinction matters for an accurate hackathon demo.

---

## ✨ Features

| Feature | Included in this version |
|---|---|
| Streamlit user interface | Website source selection, redesign method, status messages, metrics, previews and downloads |
| **ZIP website input** | Validates a ZIP and loads its supported HTML, CSS, images, fonts and other static assets |
| **URL / Wayback recovery** | Finds an Internet Archive snapshot, with automatic or selected-year lookup |
| **Multiple HTML pages** | Analyzes and redesigns all accepted HTML pages, not just `index.html` |
| **Website analysis** | Examines page structure, headings, text, links, images, CSS colors and missing local references |
| **Before / After** | Side-by-side preview of the **same chosen page** |
| **Safe CSS refresh** | Applies consistent, non-AI visual improvements across the site |
| **AI integration interface** | Uses a configured JSON HTTP endpoint or accepts team-produced JSON edits |
| **Export files** | Downloads original accepted website ZIP, redesigned website ZIP and AI input JSON |
| **Wayback report** | Shows recovered/failed/unattempted pages and assets, with a downloadable JSON report |
| **Validation & tests** | Includes ZIP/security, preservation, Wayback, integration and analyzer tests |

## 🖥️ How to run

**Requirements:** Python **3.11 or newer** and pip. Use these commands in **Windows PowerShell** from the repository root:

```powershell
# 1. Create a virtual environment
python -m venv .venv

# 2. Install dependencies
.\.venv\Scripts\python.exe -m pip install -r full_site\requirements.txt

# 3. Launch the runnable application
cd full_site
..\.venv\Scripts\python.exe -m streamlit run app.py
```

Open the local Streamlit address displayed in your terminal (typically `http://localhost:8501`).

**Alternative on Windows:** Run `full_site/RUN_WINDOWS.bat`. The launcher creates a local environment when needed and starts the full-site application.

> **Important:** Do **not** launch the root-level `app.py` from this ZIP. It is a preserved earlier UI file that imports `services.analyzer` and `services.ai_redesign`, which are not present at the repository root. The working entry point for this submitted version is **`full_site/app.py`**.

### Quick offline demo (ZIP)

1. Open the Streamlit app.
2. Choose **Upload ZIP**.
3. Upload `full_site/examples/sample_website_404_afterlife.zip`.
4. Select **Safe CSS refresh (works now)**.
5. Click **♻️ Revive Entire Website**.
6. Select an HTML page to inspect it in the **Before / After** comparison.
7. Download **404_afterlife_redesigned_site.zip**.

The sample ZIP workflow can run without Internet Archive after dependencies are installed.

### Demo using a URL (Internet Archive)

1. Choose **Recover from URL**.
2. Enter a public `http://` or `https://` website address.
3. Select **Automatic (closest)** or **Choose Year**.
4. Click **♻️ Revive Entire Website**.
5. Inspect the selected capture date, recovered pages/assets and recovery warnings.
6. Compare any recovered page and download the available recovered website.

Internet Archive must have an available capture, and **recovery may be incomplete**. A chosen year must have a matching capture.

---

## 🔄 Workflow

```text
                      404 AFTERLIFE
                            |
                   Choose website source
                     /             \
              Upload ZIP        Recover from URL
                   |                  |
           Validate ZIP        Validate public URL
                   |                  |
            Load site files     Find Wayback capture
                   |                  |
                   |           Recover pages/assets
                   \                  /
                    \                /
                     Analyze all pages
                            |
                  Choose redesign method
                   /         |          \
          Safe CSS refresh  Team AI    Import AI JSON
             (non-AI)       endpoint
                   \         |          /
                    Validate / build output
                            |
                Compare the same selected page
                            |
               Download ZIP / reports / AI JSON
```

## 🎨 Redesign options

**1. Safe CSS refresh (default demo)**  
A deterministic design update that adds shared styling to site pages while retaining the original site files. **No AI model is involved in this mode.**

**2. Team AI endpoint**  
Sends the original HTML/CSS and asset manifest to an explicitly configured trusted service. The app validates the returned page edits and keeps original binary assets. This requires an external team service; none is bundled.

**3. Import team AI JSON**  
Accepts a `.json` response containing updated HTML for **every original HTML page** and optionally modified original CSS files. This is useful for connecting another teammate's AI output without running a live endpoint.

Example AI response format:

```json
{
  "files": {
    "index.html": "<!doctype html><html><head></head><body>...</body></html>",
    "about.html": "<!doctype html><html><head></head><body>...</body></html>"
  }
}
```

These are **example path names**, not a required fixed set. The JSON must use the actual existing paths in the uploaded/recovered site and return all original HTML pages. Refer to [`full_site/TEAM_AI_INTERFACE.md`](full_site/TEAM_AI_INTERFACE.md) for the complete interface specification.

### Optional team endpoint configuration

Set these variables **before** launching Streamlit:

```powershell
$env:AFTERLIFE_AI_ENDPOINT = "http://127.0.0.1:8000/redesign"
# Only if the team endpoint requires authorization:
$env:AFTERLIFE_AI_API_KEY = "your-secret-token"
```

- A remote AI endpoint must use **HTTPS**; local HTTP is permitted for `localhost` / `127.0.0.1`.
- Only submit website content to a service you trust.
- The app checks the structure and preservation of returned HTML/CSS. It **does not verify that the imported result was actually AI-generated**.
- It does not run Gemma, Ollama or any model on its own.

---

## 📦 ZIP validation and content preservation

The ZIP importer accepts static website files under the following bounds:

| Check | Limit / behavior |
|---|---|
| ZIP file size | Up to **15 MiB** compressed |
| ZIP entries | At most **350** |
| Single supported file | At most **7 MiB** |
| Total supported uncompressed content | At most **45 MiB** |
| Required pages | At least one `.html` or `.htm` file |
| Paths | Rejects unsafe traversal/absolute paths, duplicate names, symlinks and special files |
| Unsupported file types | Omitted with a warning |

The accepted website bundle preserves supported original static assets. Original JavaScript is **retained in ZIP exports but not executed in the preview**. The original ZIP download represents the **accepted files**, not necessarily a byte-identical copy of the uploaded ZIP.

## 🕰️ Wayback recovery and its limits

The URL workflow queries Internet Archive to locate an available snapshot. The bounded same-host recovery is limited to **12 pages, 60 assets and 20 MiB total**, with a **3 MiB resource limit**. Recovered references are rewritten when possible.

The app reports:

- Discovered, recovered, failed and unattempted pages.
- Discovered, recovered, failed and unattempted assets.
- Missing resources, off-host assets and archive limitations.
- The archive capture used for the result.

Successful archive requests may be cached locally in `full_site/.cache/wayback.sqlite3`. HTTP **429 rate limits** are handled with a cooldown; cached successes may remain usable. There is **no independent archive provider fallback**. If Wayback is unavailable, use ZIP upload instead of repeatedly clicking Revive.

## 🔍 Analysis and preview

The interface presents HTML page counts, updated-page counts, output-file counts, missing-reference counts and detailed analysis. Users can select an individual page to compare before and after versions side by side.

This is a **static preview**, not a full browser recreation: JavaScript is disabled, form submissions are blocked and remote resources are restricted. Local images, CSS and fonts are included when available. Preview behavior may differ from the downloaded site's behavior.

---

## 🗂️ Repository structure

```text
After_life-feature-ui/
├── README.md                         # Project overview (this document)
├── app.py                            # Preserved legacy UI; not the working entry point
├── analyzer.py                       # Original analyzer retained for compatibility
├── pytest.ini                        # Test configuration
├── analysis_result.json              # Existing sample analysis output
├── sample_site/                      # Root-level sample HTML files
├── sample_site.zip                   # Root-level sample ZIP
├── test_run.py / test_links.py        # Standalone demo scripts
├── test_zip.py                       # Standalone ZIP demo script
├── tests/
│   └── test_analyzer.py              # Root analyzer tests
└── full_site/
    ├── app.py                        # MAIN Streamlit app: run this file
    ├── README.md                     # Additional full-site notes
    ├── TEAM_AI_INTERFACE.md          # AI team exchange contract
    ├── RUN_WINDOWS.bat               # Windows launcher
    ├── requirements.txt              # Dependencies
    ├── examples/
    │   └── sample_website_404_afterlife.zip
    ├── services/
    │   ├── site_bundle.py            # ZIP validation, site files and ZIP export
    │   ├── archive_site.py           # Wayback full-site recovery and caching
    │   ├── security.py               # URL validation
    │   ├── analysis.py               # Multi-page HTML/CSS analysis
    │   ├── preview.py                # Restricted page preview
    │   ├── redesign.py               # Deterministic CSS refresh
    │   ├── ai_bridge.py              # AI HTTP/JSON integration and validation
    │   ├── encoding.py               # HTML text handling
    │   ├── archive.py                # Legacy archive support
    │   └── reconstruct.py            # Legacy reconstruction support
    └── tests/                        # Full-site/security/integration tests
```

## 🧪 Tests

From the repository root, after installing requirements:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest_tmp
.\.venv\Scripts\python.exe -m compileall -q full_site analyzer.py
```

The suite includes tests for the analyzer, ZIP handling, content preservation, all-page processing, Wayback fallbacks/rate limits, AI validation and integration behavior. These tests do not themselves demonstrate a successful live AI redesign or complete live Wayback recovery.

**Verification of this uploaded ZIP in the documentation environment:** Python syntax compilation completed, and `tests/test_analyzer.py` passed **7/7** tests. The entire Streamlit suite was **not re-run here** because Streamlit was not installed in this inspection environment. The original committed README references earlier Windows verification; this document does not present that as a fresh test result.

## 👩‍💻 Team and responsibilities

| Team member | Project workstream |
|---|---|
| **Malak** | **CS / software development:** Streamlit interface, full-site user workflow, before/after selection, ZIP/URL inputs, analysis presentation, exports, tests and integration surfaces |
| **Sozan** | Content-preservation workstream |
| **Rana** | AI redesign/model integration workstream |

**Scope note:** This `feature/ui` README documents **Malak's submitted UI/software revision** and the features present in that repository snapshot. It does not claim that Malak authored all reused preservation or AI components. Actual model execution depends on a connected team service or imported result.

## 📸 Screenshots and demo

Add screenshots to a `docs/screenshots/` folder when available, and uncomment the links below:

```markdown
<!-- ![404 Afterlife — homepage](docs/screenshots/home.png) -->
<!-- ![ZIP upload and redesign options](docs/screenshots/upload.png) -->
<!-- ![Before and After comparison](docs/screenshots/before-after.png) -->
<!-- ![Full-site reports and ZIP downloads](docs/screenshots/downloads.png) -->
```

**Suggested demo flow:** Upload sample ZIP → Safe CSS refresh → select `index.html` and another page → compare both views → inspect missing-reference metrics → download redesigned ZIP. Optionally repeat with a live Wayback URL if the Archive is responding.

## ⚠️ Limitations and responsible use

- This is a **hackathon prototype**, not a guaranteed website restoration service.
- Server-side PHP/ASP code, databases, authentication, external services and JS-driven application behavior are not reconstructed.
- Wayback snapshots can be missing, rate-limited, partial or broken; recovered counts do not guarantee site completeness.
- Unknown scripts preserved in output ZIPs require review before deployment.
- The preview's restrictions are not a production-grade isolation boundary for untrusted sites. Public hosting requires stronger sandboxing and infrastructure security.
- Content-preservation and broken-reference checks are heuristic; inspect exported pages before publishing.
- Only process and redistribute content you have permission to use.
- Do not commit `.venv/`, local caches, private uploads, tokens, API keys or generated sensitive exports.

---

**404 Afterlife · Hacktoberfest 2026 · First submitted `feature/ui` version (Malak)**
