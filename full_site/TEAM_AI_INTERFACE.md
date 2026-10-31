# AI integration handoff for Rana and Suzy

**Goal:** refactor the user's **real website**, not create an unrelated replacement. Malak's backend owns ingestion, file paths, previews, validation and ZIP export; the AI service produces revised **HTML/CSS files**.

## Request format

```json
{
  "task": "modernize_existing_website",
  "homepage": "index.html",
  "files": {
    "index.html": "<!doctype html>... original HTML ...",
    "about.html": "<!doctype html>... original HTML ...",
    "css/style.css": "body { background: bisque; }"
  },
  "assets": ["images/logo.svg", "images/product.png"],
  "rules": ["Preserve all original text, links, image references and page count", "Return HTML/CSS edits for the existing paths only", "Do not include JavaScript, forms that send data, or external resources", "Use one consistent responsive design across all HTML pages"]
}
```

**One AI HTTP request** receives the whole site's HTML/CSS (maximum 1.2 MB combined). If larger, the current MVP rejects it; a future service can implement paging/batching.

## Response format (REQUIRED)

```json
{
  "files": {
    "index.html": "<!doctype html>... COMPLETE revised index HTML ...",
    "about.html": "<!doctype html>... COMPLETE revised about HTML ...",
    "css/style.css": "/* Revised site-wide CSS */ ..."
  }
}
```

- Include **every original HTML page** in `files`, even if a particular page's HTML stays the same. Including CSS files is optional.
- Do NOT change file names, create JS, remove original text, drop original image/anchor URLs, or add invented products/business details.
- Use a consistent header/footer and responsive CSS. Return complete file contents, not a Markdown code fence or a patch/diff.
- The backend refuses changes that fail path, content, link/image or script checks. Visual quality still needs human review.
- For now, the backend never executes AI-produced JavaScript, and never treats the baseline CSS upgrade as AI.

## Integration options

1. **Offline demo**: write the response JSON to a file and choose `Import team AI JSON` in Streamlit.
2. **API**: expose a trusted `POST /redesign` endpoint accepting the JSON request, returning JSON response, and configure `AFTERLIFE_AI_ENDPOINT` on the Streamlit server. HTTPS required for remote addresses; local HTTP permitted.

No third-party model, API key or model output is included in this source package.
