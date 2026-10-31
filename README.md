# 🕸️ 404 Afterlife

**Dead websites, reborn — restore real pages, modernize their design, and keep their content and assets.**

**Hacktoberfest 2026 · Ghost in the Machine · Malak's second CS/UI revision (`review/afterlife-malak`)**

404 Afterlife is a **Streamlit-based prototype for preserving and modernizing static websites**. It accepts an uploaded website ZIP or attempts to recover a public archived website, analyzes its pages and references, applies a design update, presents **synchronized Before / After previews**, and exports the website as a ZIP.

This document describes the files **actually included in the second revision**. The runnable application is intended to be **`full_site/app.py`**, not the preserved root-level `app.py`.

> **Current integration blocker:** `full_site/app.py` imports `services.local_ai.redesign_with_local_gemma`, but **`full_site/services/local_ai.py` is missing from this uploaded revision**. Consequently, the Streamlit entry point cannot launch as shipped, including in CSS-only mode. Restore the intended local-AI module or update the app's imports and method selection before running the UI. **The UI's Gemma option is not proof that Gemma works in this ZIP.**

---

## ✨ Features included in V2

| Area | What the code implements |
|---|---|
| **Streamlit workflow** | Choose a website source, select a redesign method, view results and download files |
| **ZIP upload** | Load supported static website files with file-count, size and path security limits |
| **URL recovery** | Try **Internet Archive / Wayback Machine** first; if unavailable or unusable, try **Arquivo.pt** |
| **Multi-page handling** | Analyze and process every accepted HTML page, not just the homepage |
| **Broken-link diagnostics** | Report missing local files and missing in-page anchors, plus links left pointing to an online archive |
| **CSS refresh** | Apply a consistent **non-AI** CSS modernization layer to the site, keeping original content/assets |
| **Local Gemma UI option** | A selectable `gemma3:1b` / Ollama path is written in the UI, but the imported module is **not included** |
| **Synchronized comparison** | Before and After views follow supported internal-page navigation together; Back and Home controls |
| **Static preview protections** | Local CSS/assets included where available; scripts/forms restricted, remote loads blocked in preview |
| **Recovery statistics** | Show archive provider, capture date, counts of discovered/recovered/failed/unattempted pages and assets |
| **ZIP downloads** | Export accepted original website and redesigned website as separate ZIPs |
| **Result ID** | Generate a content-derived identifier used in the redesigned download filename |
| **Tests** | Extended coverage for archive-provider fallback, broken references, synchronized navigation, and preview/export behavior |

**What this project is not:** It does not recreate databases, PHP/ASP backends, dynamic scripts, every historical resource, or a pixel-perfect original layout. Archive recovery and broken-link checks are best-effort/static.

## 🔄 What changed since Malak's V1 (`feature/ui`)

| V1 | V2 revision |
|---|---|
| URL recovery only through Wayback | **Wayback → Arquivo.pt** fallback in `archive_fallback.py` and `arquivo.py` |
| Separate selected-page Before / After | **Synchronized** internal navigation in `preview_navigation.py` |
| Missing-reference summary | More detailed **missing-file / missing-anchor link issues** |
| Generic ZIP output name | **Content-derived result ID** in redesigned ZIP filename |
| Safe CSS, remote team endpoint, imported team JSON in the UI | UI now exposes **Safe CSS** and **Local Gemma** (the latter is incomplete in the provided ZIP) |
| Earlier styling, encoding and preview rules | Updated navigation/button styling, UTF-8 handling and media-aware CSS import preview |
| Original test suite | Added tests for fallback provider, links, navigation and preview/export parity |

> `services/ai_bridge.py` and `TEAM_AI_INTERFACE.md` remain in V2, but **this revision's Streamlit UI no longer exposes the old “Team AI Endpoint” / “Import Team AI JSON” controls**. The files describe a reusable integration contract, not currently selectable V2 UI actions.

---

## 🛠️ Installation and launch

### Requirements

- Python **3.11+** recommended, with `pip` and virtual environments.
- Dependencies declared in `full_site/requirements.txt`: `streamlit`, `requests`, `beautifulsoup4`, `defusedxml`, `pytest`.
- Internet access for initial dependency installation and URL/archive recovery.
- **Only if/when local AI is integrated:** a working Ollama installation, the `gemma3:1b` model, and the **missing `services/local_ai.py` integration module**.

### Windows PowerShell

Run from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r full_site\requirements.txt
cd full_site
..\.venv\Scripts\python.exe -m streamlit run app.py
```

Or, after resolving the missing module, run `full_site/RUN_WINDOWS.bat` (it creates a `.venv` under `full_site/`, installs dependencies, and starts Streamlit).

**Before launching:** This upload is **not runnable unchanged** due to `services.local_ai` being missing. The commands above describe the intended startup procedure **after** that issue is corrected. Do not expect the batch file to fix a missing source module.

**Do not start the repository-root `app.py`:** it is an older preserved UI and imports service modules that are not present in the root project.

### macOS / Linux (after fixing the missing module)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r full_site/requirements.txt
cd full_site
python -m streamlit run app.py
```

---

## 🚀 Demonstration workflow

### Option A — upload a ZIP (can work offline after setup)

1. Open the repaired Streamlit application.
2. Select **Upload ZIP**.
3. Choose `full_site/examples/sample_website_404_afterlife.zip`.
4. Select **Safe CSS refresh (works now)** — this method does **not** use AI.
5. Click **♻️ Revive Entire Website**.
6. Inspect file/page metrics and any missing-reference warnings.
7. Select `index.html`, `about.html`, or another page available in the uploaded ZIP.
8. Click an internal link in the preview, or use **Back**/**Home**; the two previews are designed to stay on the same page.
9. Download both the original accepted website ZIP and the redesigned website ZIP.

### Option B — recover from a URL

1. Select **Recover from URL** and enter a public `https://` or `http://` website URL.
2. Choose **Automatic (closest)** or **Choose Year**.
3. Start recovery; the application attempts **Wayback** first, then **Arquivo.pt** if the primary provider does not yield a usable copy.
4. Check the **archive provider**, **capture timestamp**, and **recovery coverage report**.
5. Review any missing pages, assets or online-only archive links.
6. Compare recovered pages and download the resulting ZIP.

**Note:** Having a valid URL does not guarantee either archive has a snapshot. For specific years, the returned capture must match the selected year. Avoid repeatedly submitting the same request during provider rate limits.

### Option C — local Gemma (integration incomplete)

The V2 screen includes **Local Gemma (Ollama)** and refers to `gemma3:1b`. However, the required `full_site/services/local_ai.py` file is absent. To demonstrate real local AI, the team must supply and test that module, confirm a running Ollama/model, and re-run the application and tests. **Do not present a CSS-only demo as model-generated AI.**

---

## 🧠 Processing pipeline

```text
                          404 AFTERLIFE
                                |
                 Choose website source
                    /                     \
         Website ZIP                   Public URL
              |                            |
   Validate entries & paths      Validate URL + year
              |                            |
    Read supported files         Wayback Machine
              |                            |
              |                Failure / no usable capture?
              |                            |
              |                         Arquivo.pt
              |                            |
              +----------> SiteBundle <---+
                                |
                  Analyze ALL accepted pages
                                |
                      Choose redesign
                     /               \
              Safe CSS refresh     Local Gemma UI*
              (deterministic)      (*module missing)
                     \               /
                      Output SiteBundle
                                |
                Analyze missing links/assets
                                |
             Synchronized Before / After preview
                                |
                 Export ZIPs & recovery report
```

### Website preservation

- The input pipeline retains supported HTML, CSS, images, fonts, JavaScript and static assets as files within a `SiteBundle`.
- ZIP security checks reject traversal/unsafe filenames, duplicate paths, encrypted entries, symlinks and unsupported special file types.
- The **original website download** contains accepted files, **not necessarily a byte-for-byte copy of the uploaded ZIP**.
- JavaScript may be retained in exported files, but it is **not executed in the preview**; review unknown scripts before deploying the exported site.

### ZIP limits

| Check | Current limit |
|---|---|
| Compressed ZIP | **15 MiB** |
| Archive entries | **350** maximum |
| Individual supported file | **7 MiB** |
| Total supported uncompressed content | **45 MiB** |
| HTML requirement | At least one `.html` / `.htm` file |

Unsupported extensions may be omitted with a warning; this prototype is intended for **static sites**.

### Archive-provider recovery

- `services/archive_fallback.py` validates the URL and coordinates the provider attempts.
- `services/archive_site.py` implements bounded Wayback recovery; `services/arquivo.py` adds a separate provider route.
- The crawler's limits are **12 HTML pages**, **60 assets**, **20 MiB total**, and **3 MiB per fetched resource**.
- Same-host resources may be downloaded and local references rewritten. Missing pages can remain online archive links where available; their reachability is **not guaranteed**.
- Archive records can be incomplete, external assets may be omitted, and a chosen timestamp does not mean every resource was preserved on the same date.
- Cached responses and provider-specific 429 cooldowns reduce unnecessary retries. Arquivo.pt fallback is **not** a guarantee against all archive outages.

### Before / After and broken links

- `services/preview_navigation.py` composes a shared navigation view so supported internal links, Home and Back affect both previews.
- Its preview embedding has limits and does not reproduce a complete live browser session.
- `services/analysis.py` records HTML pages, links, images, headings, paragraphs, colors, missing local paths and missing in-page anchors.
- External-link availability is **not actively checked**; the analysis is static.
- Preview sanitization can differ from a downloaded site's native browser behavior, despite using the same underlying output bundle.

---

## 🗂️ Repository layout

```text
After_life-review-afterlife-malak/
├── README.md                         # Replace with this V2 README
├── app.py                            # Legacy root UI; NOT the working entry point
├── analyzer.py                       # Original analyzer kept in the repository
├── pytest.ini                        # Tests configured for root and full_site
├── sample_site/                      # Older sample pages
├── tests/test_analyzer.py            # Analyzer tests
└── full_site/
    ├── app.py                        # Intended Streamlit application (blocked by missing local_ai.py)
    ├── requirements.txt              # Installation dependencies
    ├── RUN_WINDOWS.bat               # Windows launcher
    ├── TEAM_AI_INTERFACE.md          # Legacy/reusable AI JSON handoff contract
    ├── README.md                     # Earlier full-site project notes (not fully current for V2)
    ├── examples/
    │   └── sample_website_404_afterlife.zip
    ├── services/
    │   ├── site_bundle.py            # ZIP validation, path resolution, export
    │   ├── archive_site.py           # Wayback recovery, caching, rate limits
    │   ├── archive_fallback.py       # Wayback → Arquivo.pt orchestration (NEW)
    │   ├── arquivo.py                # Arquivo.pt search/replay/recovery (NEW)
    │   ├── analysis.py               # Multi-page analysis and link diagnostics
    │   ├── preview.py                # Sanitized, embedded page preview
    │   ├── preview_navigation.py     # Synchronized navigation shell (NEW)
    │   ├── redesign.py               # Safe CSS refresh, shared styling
    │   ├── encoding.py               # Charset handling
    │   ├── ai_bridge.py              # Preserved AI JSON validation/backend contract
    │   ├── security.py               # Input URL safety validation
    │   └── local_ai.py               # REQUIRED BY app.py; MISSING IN THIS ZIP
    └── tests/
        ├── test_archive_provider_fallback.py   # NEW
        ├── test_broken_links.py                # NEW
        ├── test_preview_navigation.py          # NEW
        ├── test_preview_export_parity.py       # NEW
        └── ...                                 # Existing full-site tests
```

`local_ai.py` above is **shown as a missing required module**, not as a file supplied in the archive.

---

## 🧪 Testing and verification

### Run locally, after installing dependencies

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest_tmp
.\.venv\Scripts\python.exe -m compileall -q full_site analyzer.py
```

The test collection covers analyzer behavior, ZIP/path validation, original content preservation, archive recovery, provider fallback, rate limiting, link diagnostics, navigation, AI-bridge validation, previews and selected Streamlit integration tests.

### Inspection of the uploaded V2 ZIP — 31 October 2026

- Static inspection confirmed that **`services/local_ai.py` is absent** while `full_site/app.py` imports it.
- In the inspection environment, `streamlit` was **not installed**. A full `pytest` run stopped at collection with `ModuleNotFoundError: No module named 'streamlit'` in `full_site/tests/test_integration.py`.
- A partial run excluding `test_integration.py` produced **76 passed / 4 failed**. One of those failures is another test importing the unavailable Streamlit package; the other three involve AI-bridge/encoding or CSS-preservation expectation mismatches.
- **This revision has not been verified as a fully passing, runnable release.** A successful live archive crawl and a working local Gemma model were **not demonstrated** by this inspection.

Before submission, restore the missing AI integration or remove the dangling import/UI path, install all dependencies, resolve the failing tests, and verify both ZIP and URL demos end to end.

---

## 👩‍💻 Team and contribution scope

| Contributor / workstream | Contribution context |
|---|---|
| **Malak — CS / UI and full-site workflow** | Streamlit screens, website-source selection, multi-page preview/navigation, ZIP/URL flows, diagnostics and download user experience; this README documents her second reviewed branch |
| **Sozan — Content Preservation** | Separate content-preservation contribution used in the shared 404 Afterlife project |
| **Rana — AI** | Separate AI model/redesign integration workstream |

This repository snapshot incorporates shared project code. **The presence of a module in this branch does not mean Malak authored every service in it.** Git commits and pull requests are the source of truth for line-by-line attribution. Local Gemma is an integration target, not verified functionality in this ZIP.

## 📷 Screenshots and demo

Add verified screenshots to a `docs/screenshots/` folder, then uncomment these examples:

```markdown
<!-- ![404 Afterlife — source selection](docs/screenshots/source.png) -->
<!-- ![Recovery coverage and link analysis](docs/screenshots/recovery.png) -->
<!-- ![Synchronized Before / After](docs/screenshots/before-after.png) -->
<!-- ![Complete ZIP downloads](docs/screenshots/downloads.png) -->
```

**Suggested V2 demo:** Explain V1 → V2 additions → upload the sample ZIP → apply **Safe CSS refresh** → navigate between real site pages in synchronized previews → inspect missing links → download redesigned ZIP → optionally attempt a public archive URL to demonstrate Wayback / Arquivo.pt fallback. Only include a Gemma segment after the missing integration is fixed and the model has actually been run.

---

## ⚠️ Limitations and safe use

- **Prototype, not production hosting:** Untrusted HTML/CSS, saved JavaScript and archived content require isolation and security review before public deployment.
- ZIP security limits and URL checks reduce risk but do not eliminate all archive, network, DNS or browser-security threats.
- Browser preview disables scripts/forms and blocks remote content; the exported site may behave differently when opened outside the preview.
- Safe CSS refresh is **not AI**, and the current local Gemma UI option is incomplete without its missing module.
- Missing-link checks do not verify every remote URL and cannot infer site completeness from a partial ZIP or an archive.
- Only upload or recover sites you have the rights and permission to process.
- Do not commit virtual environments, local caches, tokens, secrets, private uploads or generated customer site exports.

---

**404 Afterlife · Hacktoberfest 2026 · Second CS/UI revision**
