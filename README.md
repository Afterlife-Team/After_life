[README.md](https://github.com/user-attachments/files/34223518/README.md)
# 🕸️ 404 Afterlife — Dead Websites, Reborn

**Preserve the pages. Protect the content. Revive the design.**

404 Afterlife is an open-source hackathon prototype that helps restore and modernize older static websites without treating their history as disposable. Upload a website ZIP or attempt to recover a historical snapshot from the Internet Archive, inspect its pages and missing references, apply a consistent redesign, compare the *same* page before and after, and export the complete result.

> Built for the **Hacktoberfest 2026 Open-Source AI Challenge — Week 4: Ghost in the Machine**. Developed by a three-person team: **Rana, Sozan (Suzy), and Malak**.

**Repository:** [404 Afterlife on GitHub](https://github.com/sozan-alkouz/afterlife)  
**Demo:** _Add a verified demo video or deployed URL here before submission._  
**DEV submission:** _Add the published article URL here._

## ✨ Why we built it

The web contains abandoned personal sites, old portfolios, community pages, and forgotten projects. A redesign should not mean throwing away their original content, internal links, or assets. **404 Afterlife** approaches modernization as *preservation first*: analyze the existing site, update its presentation, and measure what remains intact.

## 🚀 What the app does

| Capability | Description |
| --- | --- |
| **Upload ZIP** | Process a packaged static website containing HTML, CSS, images, and other assets. The UI specifies a **15 MB compressed ZIP limit**. |
| **Recover from URL** | Attempt to locate and retrieve an Internet Archive/Wayback snapshot, automatically or by selected year. Coverage depends on archive availability and rate limits. |
| **Whole-site processing** | Work with the site's discovered HTML pages rather than only rewriting the homepage. |
| **Static site analysis** | Report page/file counts and missing local links or assets detected by the analyzer. |
| **Safe CSS refresh** | Apply a deterministic, **non-AI** styling baseline for comparison or fallback. |
| **Local Gemma redesign** | Use **Gemma 3 1B** via **Ollama** to select a shared design locally. The application is intended to preserve existing content and assets. |
| **Team AI endpoint** | Optional configurable integration for a separate AI redesign service. |
| **Import AI JSON** | Apply edits supplied as JSON; importing a file alone does not verify that it was AI-generated. |
| **Before / After** | Compare the *same selected HTML page* in side-by-side static previews. |
| **Download** | Export original and redesigned website ZIPs, AI input JSON, and a recovery report when applicable. |

### What makes this different?

- **Site-wide consistency:** modernization targets multiple HTML pages and shared visual styling.
- **Content-preservation emphasis:** keep real page text, paths, links, and bundled assets rather than generating an unrelated replacement website.
- **Auditable results:** show counts, missing references, redesign method, and archive recovery coverage.
- **Local open-weight AI:** the Gemma path runs through Ollama without requiring a proprietary model API.
- **Honest baselines:** a safe CSS refresh is explicitly labeled **not AI**.

## 🧭 User journey

1. **Choose source:** `Upload ZIP` (recommended for a reproducible demo) or `Recover from URL` (experimental).
2. **Choose redesign method:** `Local Gemma (Ollama)`, `Safe CSS refresh`, `Team AI endpoint`, or `Import team AI JSON`.
3. Click **♻️ Revive Entire Website**.
4. Review the full-site analysis, counts, missing references, and any archive recovery warnings.
5. Select an HTML page and inspect the **Before / After** previews.
6. Download the redesigned website ZIP and inspect it locally before deployment.

## 🏗️ Architecture

```text
                      ┌───────────────────────────────┐
                      │       Streamlit UI            │
                      │          app.py               │
                      └──────────────┬────────────────┘
                                     │
                     ┌───────────────┴────────────────┐
                     ▼                                ▼
               Upload ZIP                       Wayback URL
                     │                                │
             site_bundle.py                   archive_site.py
                     └───────────────┬────────────────┘
                                     ▼
                              Website bundle
                                     │
                              analysis.py
                                     │
             ┌───────────────────────┼────────────────────────┐
             ▼                       ▼                        ▼
      Safe CSS refresh        Local Gemma/Ollama       Endpoint / JSON
        redesign.py              local_ai.py             ai_bridge.py
             └───────────────────────┼────────────────────────┘
                                     ▼
                              Updated bundle
                                     │
                        Analyze + preview + export
                          preview.py / to_zip()
```

**Design principle:** Python handles structured file processing and deterministic checks; the AI model assists with visual design decisions. AI output should be validated before use, not trusted as authoritative source content.

## 🧰 Technology stack

| Layer | Technology | Purpose |
| --- | --- | --- |
| Application | Python, Streamlit | UI and orchestration |
| HTML processing | Beautiful Soup / HTML parsing utilities | Extract and inspect page structure |
| Local AI | Google Gemma 3 1B, Ollama | Local open-weight design assistance |
| Archive recovery | Internet Archive / Wayback Machine | Historical snapshot retrieval |
| Website output | HTML, CSS, ZIP | Portable static site export |
| Tests | pytest | Unit and integration testing |
| Collaboration | Git, GitHub | Branches, pull requests, version control |

> Dependency versions should be taken from the repository's actual `requirements.txt`. Do not treat the table as a complete installation lockfile.

## 📁 Code organization

The integrated implementation discussed by the team includes the following modules. **Confirm the final directory layout on `main` before publishing this section:**

```text
404-afterlife/
├── full_site/                   # Integrated multi-page Streamlit application
│   ├── app.py                   # Source selection, redesign, analysis, preview, export
│   ├── services/
│   │   ├── site_bundle.py       # ZIP ingestion, website bundle, ZIP export
│   │   ├── encoding.py          # Text/HTML decoding
│   │   ├── analysis.py          # Full-site reference analysis
│   │   ├── preview.py           # Sandboxed/static page preview
│   │   ├── redesign.py          # Deterministic CSS refresh
│   │   ├── local_ai.py          # Local Gemma via Ollama
│   │   ├── ai_bridge.py         # External AI endpoint and JSON changes
│   │   ├── archive_site.py      # Wayback snapshot selection/recovery
│   │   └── security.py          # URL safety checks
│   └── tests/                   # Integrated tests (verify exact filenames)
├── requirements.txt            # May be at repository or application root
└── README.md
```

Other team branches also contained analyzer, AI-engine, renderer, validator, missing-page-recovery, and multi-page-redesign modules. Their presence in the final branch should be verified rather than assumed.

## ⚙️ Local setup

### Prerequisites

- Python compatible with the checked-in dependencies (Python **3.11** is a reasonable starting point; confirm supported versions in the repository).
- Git and a terminal (examples below use **Windows PowerShell**).
- Ollama, **only** for the local Gemma redesign option.

### 1. Clone

```powershell
git clone https://github.com/sozan-alkouz/afterlife.git
cd afterlife
```

If the final application lives in `full_site`, navigate there:

```powershell
cd full_site
```

### 2. Create an environment and install dependencies

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If `requirements.txt` is stored at the repository root instead, install it from that location (`..\requirements.txt` when inside `full_site`). On macOS/Linux use `python3 -m venv .venv` and `.venv/bin/python`.

### 3. Install the local model (optional, for AI mode)

Install [Ollama](https://ollama.com/), then run:

```powershell
ollama pull gemma3:1b
ollama list
```

Ensure Ollama is running. The application expects the `gemma3:1b` model for its local mode; do not substitute `gemma3:4b` without updating and testing the code.

### 4. Start the app

From the directory containing the integrated `app.py`:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open the local URL printed by Streamlit (commonly `http://localhost:8501`). If using the non-AI CSS refresh, Ollama is not required.

## 🤖 Redesign methods: what is actually AI?

| Mode shown in the UI | AI? | Notes |
| --- | --- | --- |
| `Safe CSS refresh (works now)` | **No** | Deterministic baseline; useful if the local model is unavailable. |
| `Local Gemma (Ollama)` | **Yes** | Uses local `gemma3:1b` to assist with a shared site design. |
| `Team AI endpoint` | Depends on configured service | Set `AFTERLIFE_AI_ENDPOINT` and any credentials required by the team's endpoint implementation. |
| `Import team AI JSON` | Not independently verifiable | Imports proposed HTML/CSS changes; provenance must be documented separately. |

Example import payload shape:

```json
{
  "files": {
    "index.html": "<!doctype html><html><body><h1>Preserved homepage</h1></body></html>"
  }
}
```

**Important:** This illustrates the expected JSON shape, not an instruction to replace a real page with placeholder text. Edits must preserve existing page content, paths, and references.

## 🔐 Preservation and security

The project is designed around these constraints:

- Keep the original HTML pages and bundled static assets available in the output.
- Preserve meaningful text, navigation links, image references, and existing relative paths.
- Avoid silently inventing historical content or claiming that an AI reconstruction is an authenticated original.
- Validate URL input and limit unsafe URL schemes/hosts for archive retrieval.
- Apply ZIP processing limits and reject unsafe paths where implemented.
- Present previews as **static**: scripts disabled, forms unable to submit, and external resources blocked in the integrated preview.
- Treat uploaded HTML and model output as untrusted. Review the exported files before opening or hosting them.

**Security caveat:** The output ZIP may retain original JavaScript files, even though previews disable scripts. Do not deploy unreviewed historical or user-uploaded scripts. Static previews are not a substitute for a production security review.

## 🧪 Testing and evaluation

The team previously reported **48 passing tests** across integrated UI and AI components (**35 full-site tests + 13 AI tests**) on an October 30 development snapshot. **This is historical development evidence, not a verified test result for the final `main` branch.** Re-run the complete suite before claiming a current pass count.

```powershell
# From the directory that contains the relevant tests
.\.venv\Scripts\python.exe -m pytest -q
```

Recommended demo checks:

1. ZIP ingestion rejects invalid or unsafe archives.
2. Multi-page output retains the original page count and expected filenames.
3. Internal links and asset paths resolve within the exported ZIP.
4. Text is not silently dropped or duplicated during redesign.
5. Nested pages and relative links continue to work.
6. Before/After compares the same page.
7. A failed model request yields a visible warning or controlled fallback rather than a false AI-success claim.
8. Archive failures and HTTP 429 rate limits are reported honestly.

**Development observation:** an earlier real Gemma whole-site run encountered an invalid design plan and used a fallback. Do not claim that the Gemma end-to-end flow is fully reliable until it has been re-tested on the final integrated version.

### Suggested reproducible evaluation table

| Metric | Baseline | Redesigned | How to verify |
| --- | --- | --- | --- |
| HTML page count | _Record_ | _Record_ | Count pages in ZIPs |
| Missing internal references | _Record_ | _Record_ | Analyzer report |
| Preserved text | _Record_ | _Record_ | Automated checks + manual review |
| Preserved images/assets | _Record_ | _Record_ | File/path comparison |
| Local AI runtime | N/A | _Record_ | Timed local run |
| Test suite | _Record_ | _Record_ | `pytest -q` output |

Do not fill these cells with invented numbers. Add screenshots and the exact input fixture used.

## 📦 Outputs

- `404_afterlife_redesigned_site.zip` — exported redesigned static website.
- `404_afterlife_original_site.zip` — exported original bundle for comparison.
- `404_afterlife_team_ai_input.json` — text-based HTML/CSS input contract for the AI team.
- `404_afterlife_recovery_report.json` — archive recovery details when using Wayback.

The UI also reports source, homepage, method, HTML page count, changed page count, output file count, and missing references after processing.

## ⚠️ Known limitations

- **Archive coverage:** Wayback snapshots can be missing, incomplete, or temporarily rate-limited (HTTP 429); the archive is not a guarantee of full-site recovery.
- **ZIP completeness:** the analyzer can only verify references against files included in the uploaded bundle; it cannot prove that an original historical site was complete.
- **Static sites first:** complex server-side functionality, databases, logins, and dynamic JavaScript applications are outside the prototype's reliable restoration scope.
- **AI variability:** local Gemma can produce malformed or unsuitable design plans; fallback behavior must be inspected and disclosed.
- **Rendering differences:** a sandboxed static preview may not match a live deployed site exactly.
- **Security:** exported legacy scripts and third-party assets require review before deployment.
- **Not archival authentication:** generated or inferred content must not be presented as recovered historical fact.

## 👩‍💻 Team and contributions

| Member | Responsibility |
| --- | --- |
| **Rana** | Website analysis, HTML/content extraction, links and missing assets, AI-ready structured data, tests |
| **Sozan (Suzy)** | Local AI/Gemma integration, redesign planning, HTML rendering/validation, AI reconstruction |
| **Malak** | Streamlit frontend, ZIP/URL user workflow, Before/After UI, integration, exports, end-to-end tests |

GitHub commit history and pull requests document actual contributions; an organization or fork alone does not establish authorship. Add the three members' **GitHub and DEV profile links** before submitting the article.

## 🏆 Hackathon submission

**Event:** Hacktoberfest 2026 — Open-Source AI Challenge, Week 4: *Ghost in the Machine*  
**Challenge:** [Official DEV challenge page](https://dev.to/challenges/hacktoberfest-week4-2026-10-26)

**Theme connection:** 404 Afterlife brings forgotten corners of the web back into view, treating digital history as something to preserve rather than overwrite.

**Prize category to consider:** **Best Use of Gemma** — the project has a real local Gemma 3 1B integration. Other partner categories (such as GitHub Copilot, Render, or Sentry) should be claimed **only if the required tool was actually used and documented**, not because it appears in a plan.

Before submission, attach:

- [ ] A short, working demo video or accessible live demo
- [ ] Screenshots of the same page before and after
- [ ] A reproducible sample ZIP and its output (with permission)
- [ ] Actual `pytest` results from the final commit
- [ ] Model name, inference setup, and any fallback behavior
- [ ] Repository link and all three contributors' DEV handles
- [ ] Honest limitations and applicable prize categories

## 🛣️ Future work

- More robust archive discovery and graceful rate-limit handling
- Stronger preservation tests for text, CSS assets, and nested paths
- Reliable AI plan validation with transparent fallback reporting
- Automated GitHub Actions test runs and review checks
- Optional hosted model execution and reproducible hosted demos
- Accessibility audits and visual regression comparisons

## 🤝 Contributing

Open an issue describing the problem, work on a feature branch, add tests for behavior changes, and submit a pull request. Avoid committing secrets, downloaded third-party sites without permission, large generated ZIPs, or local `.venv` directories.

## 📜 License and responsible use

**License:** _Add the repository's actual license here; do not assume MIT or another license until a `LICENSE` file is present._

Only upload, modify, or redistribute websites and assets you own or have permission to use. An archived copy being publicly accessible does **not** automatically grant reuse rights. Credit original creators and preserve provenance when demonstrating historical material.

---

**404 Afterlife — Dead websites, reborn. Real pages, real content, a second life.**
