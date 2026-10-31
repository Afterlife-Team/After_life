# 🕸️ 404 Afterlife — Content Preservation & Full-Site Recovery

**Dead websites, reborn. Preserve the past. Rebuild the future.**

Part of **404 Afterlife**, developed for **Hacktoberfest 2026 — Ghost in the Machine**.

**Branch:** `feature/content-preservation`  
**Developer:** Sozan Alkouz  
**Repository:** https://github.com/Afterlife-Team/After_life

---

## 1. Overview

The internet is constantly evolving, but many websites disappear, become inaccessible, or lose important content over time.

404 Afterlife aims to bring forgotten websites back to life through website recovery, content analysis, preservation, and modernization.

This branch focuses on one of the project's most important challenges:

**How can we modernize an old website without losing the original information, pages, images, and navigation that made it valuable?**

The Content Preservation & Full-Site Recovery component addresses this challenge through structured HTML analysis, archive retrieval, safe redesign, and preservation validation.

Rather than simply generating a visually attractive replacement, the system attempts to retain the actual website structure and available original content.

## 2. Core Objectives

- Preserve original website content during modernization.
- Recover available historical website pages from the Internet Archive.
- Support complete static website ZIP uploads.
- Analyze HTML pages, assets, and internal references.
- Identify missing local resources and broken references.
- Apply consistent visual modernization across multiple pages.
- Validate redesigned content against the original website.
- Provide safe before-and-after comparisons.
- Export complete website bundles for further development.

## 3. Key Features

### 3.1 Website ZIP Preservation

Users can upload an existing static website as a ZIP archive.

The system processes supported files, including:

- HTML and HTM pages
- CSS stylesheets
- Images and fonts
- JavaScript files
- Other supported static assets

The ZIP processor validates file paths, archive structure, supported file types, and resource limits before processing.

**Safety limits:**

| Constraint | Limit |
|---|---|
| Compressed ZIP size | 15 MiB |
| Maximum archive entries | 350 |
| Maximum supported file size | 7 MiB |
| Total supported uncompressed data | 45 MiB |

Unsafe paths, encrypted entries, duplicate filenames, and unsupported archive structures are rejected or handled conservatively.

### 3.2 Full-Site Content Analysis

The system analyzes the HTML pages available in the website bundle.

It extracts and examines:

- Page structure
- Headings and paragraphs
- Navigation links
- Image references
- CSS colors
- Local asset references
- Missing resources

This helps identify structural and preservation problems before redesign.

The analysis is static: it does not guarantee that external websites are reachable or that JavaScript-driven features will work.

### 3.3 Wayback Machine Recovery

The recovery component integrates with the Internet Archive to locate available historical website snapshots.

Users can provide a website URL and choose either automatic snapshot selection or a requested archive year.

The system attempts to retrieve available pages and resources, rewrite recovered references, and build a local static website bundle.

**Recovery limits:**

| Resource | Limit |
|---|---|
| Pages attempted | 12 |
| Assets attempted | 60 |
| Total recovery budget | 20 MiB |
| Individual resource | 3 MiB |

Recovery results distinguish between discovered, recovered, failed, and unattempted resources.

This is important because **an archived snapshot does not necessarily contain the complete historical website**.

### 3.4 Archive Reliability and Caching

The recovery implementation includes:

- Internet Archive Availability API integration
- CDX fallback for requested-year searches
- Public URL validation
- Controlled redirect handling
- Local SQLite caching
- Rate-limit handling
- Recovery status reporting

Successful archive responses can be cached locally to reduce unnecessary repeated requests.

HTTP 429 responses trigger cooldown handling instead of aggressive repeated requests.

The system still depends on Internet Archive availability; it does not provide an independent archive source.

### 3.5 Content-Preserving Modernization

The deterministic redesign component applies a shared CSS refresh across available website pages.

Its goals are to improve readability, layout consistency, and presentation while preserving original content and assets.

The implementation includes conservative handling for more complex sites and limited navigation adjustments where appropriate.

**Important:** The CSS refresh is a non-AI baseline. It must not be described as AI-generated redesign.

### 3.6 AI Integration and Preservation Validation

The full-site workflow supports integration with the team's AI redesign component through structured JSON or a configured HTTP endpoint.

The preservation layer checks proposed changes before applying them.

Validation includes checks for:

- Unknown or unexpected file paths
- Missing original content
- Removed anchor and image references
- Changed script tags
- Changed event handlers
- Unexpected modifications to existing files

Original binary assets remain preserved.

These checks reduce the risk of content loss but are heuristic, not a formal guarantee of semantic equivalence.

The branch provides integration infrastructure; actual AI execution depends on the configured model service or supplied AI output.

### 3.7 Before-and-After Comparison

The Streamlit interface allows users to compare the same original page before and after modernization.

The preview:

- Displays corresponding original and updated pages
- Includes local styling and image resources
- Restricts script execution
- Blocks form submission
- Sanitizes SVG content
- Restricts remote resource loading

This supports visual inspection without treating arbitrary website code as fully trusted.

### 3.8 Export and Downloads

Available outputs include:

- Original accepted website bundle
- Redesigned website ZIP
- Structured AI input JSON
- Wayback recovery report, when applicable

The original bundle export contains the accepted processed files; it is not necessarily byte-for-byte identical to the uploaded ZIP.

## 4. System Architecture

```text
              WEBSITE INPUT
                    |
          +---------+---------+
          |                   |
      ZIP Upload         Website URL
          |                   |
     ZIP Validation      URL Validation
          |                   |
          |              Wayback APIs
          |                   |
          |             Archive Recovery
          |                   |
          +---------+---------+
                    |
             Website Bundle
                    |
            Full-Site Analysis
                    |
          Content & Asset Inventory
                    |
             Redesign Method
                    |
          +---------+---------+
          |                   |
       CSS Refresh        Team AI Output
          |                   |
          |             AI Validation
          |                   |
          +---------+---------+
                    |
             Updated Website
                    |
           Preservation Checks
                    |
           Before/After Preview
                    |
             ZIP / JSON Export
```

The workflow separates website retrieval, content analysis, redesign, and validation to make the implementation easier to test and maintain.

## 5. Repository Structure

The runnable full-site implementation is located in `full_site/`.

```text
After_life/
|
|-- full_site/
|   |-- app.py
|   |-- requirements.txt
|   |-- RUN_WINDOWS.bat
|   |
|   |-- services/
|   |   |-- site_bundle.py
|   |   |-- analysis.py
|   |   |-- archive_site.py
|   |   |-- redesign.py
|   |   |-- ai_bridge.py
|   |   |-- preview.py
|   |   |-- security.py
|   |   |-- encoding.py
|   |   `-- ...
|   |
|   |-- tests/
|   `-- examples/
|
|-- analyzer.py
|-- tests/
|-- sample_site/
|-- pytest.ini
`-- README.md
```

**Important modules**

| Module | Responsibility |
|---|---|
| `site_bundle.py` | Website ZIP ingestion and export |
| `analysis.py` | Full-site static analysis |
| `archive_site.py` | Internet Archive recovery |
| `redesign.py` | Deterministic CSS modernization |
| `ai_bridge.py` | AI output integration and validation |
| `preview.py` | Restricted before-and-after previews |
| `security.py` | URL and input security checks |
| `encoding.py` | HTML text decoding |
| `app.py` | Streamlit user interface |

The earlier root-level analyzer and demonstration files are retained for compatibility with the wider team project.

Use `full_site/app.py` as the entry point for this implementation.

## 6. Installation and Setup

### Requirements

- Python 3.11 or newer
- Git
- Internet access for initial dependency installation
- Windows PowerShell for the commands below

### Step 1 — Clone the repository

```bash
git clone -b feature/content-preservation https://github.com/Afterlife-Team/After_life.git
cd After_life
```

### Step 2 — Create a virtual environment

```powershell
python -m venv .venv
```

### Step 3 — Install dependencies

```powershell
.\.venv\Scripts\python.exe -m pip install -r full_site\requirements.txt
```

### Step 4 — Run the application

```powershell
cd full_site
..\.venv\Scripts\python.exe -m streamlit run app.py
```

Open the local Streamlit address displayed in the terminal.

Alternatively, run `full_site/RUN_WINDOWS.bat` on Windows.

## 7. Quick Demo

### Option A — Upload an Existing Website

1. Launch the Streamlit application.
2. Select **Upload ZIP**.
3. Upload `sample_website_404_afterlife.zip` from the examples directory.
4. Select **Safe CSS refresh**.
5. Click **Revive Entire Website**.
6. Inspect the analysis results.
7. Compare the original and updated pages.
8. Download the redesigned website ZIP.

### Option B — Recover an Archived Website

1. Select **Recover from URL**.
2. Enter a public website URL.
3. Choose automatic archive selection or a specific year.
4. Start the recovery process.
5. Review recovered pages and missing resources.
6. Apply the selected redesign method.
7. Download the resulting website and recovery report.

Archive recovery depends on snapshot availability and Internet Archive rate limits.

## 8. AI Integration Contract

The system can export HTML/CSS content and asset references as structured JSON for the team's AI component.

A configured AI endpoint may receive a request containing:

```json
{
  "task": "modernize_existing_website",
  "homepage": "index.html",
  "files": {
    "index.html": "<html>...</html>"
  },
  "assets": [
    "images/logo.png"
  ]
}
```

The AI component is expected to return updates to existing website files.

Example response:

```json
{
  "files": {
    "index.html": "<html>...updated original page...</html>"
  }
}
```

The validation layer checks proposed changes before incorporating them into the website bundle.

The objective is to preserve the original website rather than generate unrelated replacement content.

## 9. Testing and Verification

The branch includes tests covering website processing, preservation, archive recovery, security, and application integration.

Run tests from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest_tmp
```

Run syntax compilation:

```powershell
.\.venv\Scripts\python.exe -m compileall -q full_site analyzer.py
```

### Recorded Verification

The branch's documented verification run on **October 29, 2026**, using Windows and Python 3.15.2, reported:

**42 tests passed.**

Covered areas included:

- Original website analyzer
- ZIP processing and preservation
- Website bundle export
- Local reference resolution
- Text preservation
- SVG restrictions
- AI output validation
- Local HTTP AI integration stub
- Mocked archive recovery
- Rate-limit handling
- Streamlit smoke tests

Syntax compilation also passed, and a temporary Streamlit health endpoint returned a successful response.

These are recorded development results, not a claim that all live archive scenarios or actual AI model executions were tested.

## 10. Security Considerations

The implementation applies multiple defensive measures:

- Public URL validation
- Archive path validation
- ZIP entry and size limits
- Restricted archive redirects
- Static HTML analysis
- Restricted preview execution
- SVG sanitization
- AI output validation
- Controlled resource recovery
- Rate-limit and cache handling

Generated website exports should still be reviewed before public deployment.

The preview environment is not a production-grade isolation boundary.

## 11. Known Limitations

404 Afterlife is a hackathon prototype focused on static website preservation.

Current limitations include:

- Historical archives may be incomplete.
- Unavailable pages and assets cannot be reconstructed with guaranteed accuracy.
- Backend databases and server-side application logic are not recovered.
- JavaScript-dependent functionality may not work in previews.
- Off-host assets are not fully recovered.
- Static analysis cannot verify every external link.
- Preservation validation is heuristic.
- Archive APIs may impose rate limits.
- Exported JavaScript files require review before deployment.

These limitations are intentionally documented to distinguish verified preservation from speculative reconstruction.

## 12. Development Contribution

### Sozan Alkouz — Content Preservation & Full-Site Recovery

**Branch:** `feature/content-preservation`

Sozan developed the content-preservation and full-site recovery work represented in this branch.

Her contribution focuses on the technical workflow for handling existing websites, analyzing their contents, recovering available historical resources, supporting safe modernization, and validating preservation constraints.

The work includes:

- Full-site website processing
- Static website ZIP handling
- Content and asset preservation
- Wayback Machine recovery integration
- Multi-page modernization workflow
- Before-and-after comparison
- AI integration and validation interfaces
- Security and error handling
- Testing and technical verification

This branch is part of the wider **404 Afterlife** team project, developed collaboratively by Sozan, Rana, and Malak.

## 13. Future Improvements

Potential improvements include:

- More comprehensive multi-page recovery
- Improved broken-link repair
- Enhanced visual preservation comparisons
- Stronger semantic content validation
- Additional archive-source support
- Expanded AI-assisted reconstruction
- More extensive browser-based testing
- Production-grade sandboxing and deployment security

## 14. Project Information

**Project:** 404 Afterlife  
**Theme:** Ghost in the Machine  
**Event:** Hacktoberfest 2026 — Week 4  
**Branch:** `feature/content-preservation`  
**Developer:** Sozan Alkouz  
**Organization:** Afterlife-Team

**GitHub Repository:**  
https://github.com/Afterlife-Team/After_life

---

*404 Afterlife — Because forgotten websites deserve a second life.*
