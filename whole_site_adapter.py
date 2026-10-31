"""404 Afterlife: whole-site AI adapter for Malak's {files: {path: text}} contract.

One Ollama call selects a shared design plan. Python injects a consistent CSS
layer into each original HTML document without rebuilding its content/DOM.
No original paths, text, anchor/image references, scripts or assets are removed.
"""
import json
import re
from typing import Any

THEMES = {
    "ocean": {"hero": "#173c61", "bg": "#f1f7fc", "text": "#173047", "accent": "#1477bc", "panel": "#ffffff"},
    "forest": {"hero": "#194d40", "bg": "#f1f8f3", "text": "#183c33", "accent": "#267957", "panel": "#ffffff"},
    "sunset": {"hero": "#69354f", "bg": "#fff6f2", "text": "#452b3a", "accent": "#a33456", "panel": "#ffffff"},
}
LAYOUTS = {"cards", "minimal", "editorial"}
HTML_EXTENSIONS = (".html", ".htm")
EDITABLE_EXTENSIONS = HTML_EXTENSIONS + (".css",)
MAX_INPUT_BYTES = 1_200_000


class WholeSiteError(ValueError):
    pass


def _site_overview(files: dict[str, str]) -> dict[str, Any]:
    """Send a compact site-level overview to Gemma, not every full page."""
    from bs4 import BeautifulSoup

    pages = []
    for path, content in files.items():
        if not path.lower().endswith(HTML_EXTENSIONS):
            continue
        soup = BeautifulSoup(content, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        headings = [t.get_text(" ", strip=True)[:90] for t in soup.select("h1,h2")[:8]]
        pages.append({"path": path, "title": title[:100], "headings": headings})
    return {"pages": pages[:30], "page_count": len(pages), "css_count": sum(p.lower().endswith('.css') for p in files)}


def _normalize_choice(value: Any, allowed: set[str]) -> str | None:
    """Accept casing/spacing differences, but never invent an AI selection."""
    if not isinstance(value, str):
        return None
    normalized = value.strip().strip('\"\'`').strip().lower()
    return normalized if normalized in allowed else None


def _choose_plan(files: dict[str, str], use_ai: bool) -> tuple[dict[str, str], bool, str]:
    default = {"theme": "ocean", "layout": "cards"}
    if not use_ai:
        return default, False, "AI disabled"
    try:
        from ollama import chat
        instructions = (
            "You are a visual design selector, not an HTML generator. "
            "Choose exactly one theme and one layout for ALL pages. "
            "Allowed theme values: ocean, forest, sunset. "
            "Allowed layout values: cards, minimal, editorial. "
            "Output a single JSON object with exactly theme and layout, "
            "each a string. Do not add explanations, other fields, or markdown. "
            'Example valid response: {"theme":"forest","layout":"minimal"}. '
            "Do not alter or generate site content."
        )
        # Ollama structured outputs constrain Gemma's choices to real enum values.
        schema = {
            "type": "object",
            "properties": {
                "theme": {"type": "string", "enum": list(THEMES)},
                "layout": {"type": "string", "enum": sorted(LAYOUTS)},
            },
            "required": ["theme", "layout"],
            "additionalProperties": False,
        }
        response = chat(
            model="gemma3:1b",
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": json.dumps(_site_overview(files), ensure_ascii=False)},
            ],
            format=schema,
            options={"temperature": 0, "num_predict": 160},
        )
        # Ollama Python may return a mapping or a response object.
        message = response["message"] if isinstance(response, dict) else response.message
        raw = message["content"] if isinstance(message, dict) else message.content
        answer = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(answer, dict):
            raise ValueError("plan must be a JSON object")
        theme = _normalize_choice(answer.get("theme"), set(THEMES))
        layout = _normalize_choice(answer.get("layout"), LAYOUTS)
        if not theme or not layout:
            raise ValueError(
                "invalid Gemma choices: "
                f"theme={str(answer.get('theme'))[:60]!r}, "
                f"layout={str(answer.get('layout'))[:60]!r}"
            )
        return {"theme": theme, "layout": layout}, True, ""
    except Exception as exc:
        # An AI failure should never masquerade as AI success.
        return default, False, f"Gemma plan unavailable: {type(exc).__name__}: {exc}"


def _stylesheet(plan: dict[str, str]) -> str:
    c = THEMES[plan["theme"]]
    layout = plan["layout"]
    panel = "border:1px solid #dbe5ed; border-radius:16px; box-shadow:0 7px 24px #0000000d;" if layout == "cards" else (
        "border-left:4px solid var(--af-accent); border-radius:0;" if layout == "editorial" else "border-bottom:1px solid #ccd8df; border-radius:0;"
    )
    return f"""/* 404 Afterlife: shared whole-site design layer; original HTML preserved */
:root{{--af-hero:{c['hero']};--af-bg:{c['bg']};--af-text:{c['text']};--af-accent:{c['accent']};--af-panel:{c['panel']};}}
*,*::before,*::after{{box-sizing:border-box;}}
html{{scroll-behavior:smooth;}}
body{{background:var(--af-bg)!important;color:var(--af-text)!important;font-family:system-ui,-apple-system,'Segoe UI',sans-serif!important;line-height:1.7!important;margin:0;overflow-wrap:anywhere;}}
body > header,body > nav,body > main,body > footer{{width:min(1100px,calc(100% - 32px));margin-inline:auto;}}
body > header{{background:var(--af-hero)!important;color:white!important;padding:clamp(28px,5vw,64px)!important;border-radius:0 0 22px 22px;}}
body > header a{{color:white!important;}}
h1,h2,h3{{line-height:1.23;letter-spacing:-.02em;}}
h1{{font-size:clamp(2rem,4.5vw,3.4rem);}}
h2{{font-size:clamp(1.35rem,2.7vw,2rem);}}
a{{color:var(--af-accent);text-underline-offset:3px;}}
img,video,iframe,svg{{max-width:100%;height:auto;}}
nav{{display:flex;flex-wrap:wrap;gap:12px;padding:14px 0;}}
nav a{{display:inline-block;padding:8px 14px;background:var(--af-panel);border:1px solid #dce7ee;border-radius:999px;text-decoration:none;}}
main{{padding-block:24px 46px;}}
main section, main article{{background:var(--af-panel);padding:clamp(18px,2.8vw,28px);margin-block:18px;{panel}}}
button,input,textarea,select{{max-width:100%;font:inherit;}}
@media(max-width:640px){{body > header,body > nav,body > main,body > footer{{width:calc(100% - 24px);}}body > header{{padding:24px!important;}}nav{{gap:6px;}}nav a{{padding:7px 10px;}}}}

body > header h1,
body > header h2,
body > header h3 {{
    color: #ffffff !important;
}}

body nav a,
body > header nav a {{
    color: var(--af-text) !important;
    background: #ffffff !important;
    border: 1px solid #dce7ee !important;
}}
/* Pair foregrounds with surfaces, including legacy inline colors. */
body > header :is(h1,h2,h3,h4,h5,h6,p,li,span,strong,em){{color:#fff!important;}}
body > main{{background:var(--af-panel)!important;border-radius:16px;padding:clamp(20px,4vw,40px);margin-block:24px;}}
body > main :is(h1,h2,h3,h4,h5,h6,p,li,label){{color:var(--af-text)!important;}}
body > main a,body > a{{color:var(--af-accent)!important;}}
/* Flat secondary documents retain their nodes and receive the same spacing. */
body > :is(h1,h2,h3,p,ul,ol,form){{width:min(1100px,calc(100% - 32px));margin-inline:auto;}}
body > h1{{background:var(--af-hero)!important;color:#fff!important;padding:clamp(28px,5vw,64px);border-radius:0 0 22px 22px;margin-block:0 24px;}}
body > :is(h2,h3,p,ul,ol,label){{color:var(--af-text)!important;}}
body > p{{margin-block:20px;}}
body > a{{display:inline;color:var(--af-accent)!important;}}
/* Legacy documents often put inline links directly in BODY. Keep prose inline. */
body:not(:has(> main)){{width:min(1080px,calc(100% - 32px));margin:24px auto!important;padding:clamp(24px,5vw,56px);background:var(--af-panel)!important;border:1px solid #dce5e9;border-top:5px solid var(--af-accent);border-radius:18px;box-shadow:0 12px 36px #1730470a;}}
body:not(:has(> main)) > :is(h1,h2,h3,p,ul,ol,dl,form){{width:auto;margin-inline:0;}}
body:not(:has(> main)) > h1{{padding:0 0 24px;margin:0 0 24px;background:transparent!important;color:var(--af-hero)!important;border-radius:0;border-bottom:1px solid #dce5e9;font-size:clamp(2rem,5vw,3.2rem);}}
body:not(:has(> main)) > header:not(:has(h1,h2,h3,p,nav,a,img)){{display:none!important;}}
body > dl{{display:grid;grid-template-columns:minmax(160px,.32fr) minmax(0,1fr);gap:0 28px;margin-block:30px;}}
body > dl > :is(dt,dd){{margin:0;padding:18px 0;border-bottom:1px solid #e1e8ed;}}
body > dl > dt{{font-weight:650;}}
body > dl > dd{{color:var(--af-text);}}
body > dl a{{text-decoration-thickness:1px;text-underline-offset:4px;}}
@media(max-width:600px){{body > dl{{display:block;}}body > dl > dt{{border-bottom:0;padding-bottom:4px;}}body > dl > dd{{padding-top:0;margin-bottom:10px;}}body:not(:has(> main)){{width:calc(100% - 16px);margin:8px auto!important;padding:24px 20px;}}}}
form{{display:flex;flex-wrap:wrap;align-items:center;gap:12px;margin-block:24px;}}
input:not([type=checkbox]):not([type=radio]):not([type=hidden]),textarea,select{{min-width:0;min-height:44px;padding:10px 12px;background:#fff!important;color:var(--af-text)!important;border:1px solid #64748b;border-radius:8px;}}
input::placeholder,textarea::placeholder{{color:#526174!important;opacity:1;}}
button,input[type=submit],input[type=button],input[type=reset]{{min-height:44px;padding:10px 20px;background:var(--af-accent)!important;color:#fff!important;border:1px solid var(--af-accent);border-radius:8px;cursor:pointer;}}
nav a{{min-height:44px;}}
nav a:hover{{text-decoration:underline;border-color:var(--af-accent)!important;}}
button:hover,input[type=submit]:hover{{filter:brightness(.9);}}
:is(a,button,input,textarea,select):focus-visible{{outline:3px solid var(--af-accent)!important;outline-offset:3px;box-shadow:0 0 0 3px #fff;}}
button:disabled,input:disabled{{opacity:.65;cursor:not-allowed;}}
table{{display:block;max-width:100%;overflow-x:auto;}}
@media(prefers-reduced-motion:reduce){{html{{scroll-behavior:auto;}}}}
@media(max-width:640px){{body > :is(h1,h2,h3,p,ul,ol,form){{width:calc(100% - 24px);}}body > h1{{padding:24px;}}form > :is(input:not([type=checkbox]):not([type=radio]),textarea,select){{flex:1 1 180px;width:100%;}}}}
"""


def _inject_css(original: str, css: str) -> str:
    """Only add the design style and, when absent, mobile viewport metadata."""
    if "afterlife-whole-site-style" in original:
        raise WholeSiteError("Input already contains whole-site style marker")
    style = '<style id="afterlife-whole-site-style">\n' + css + '\n</style>\n'
    # Without a viewport mobile browsers render a scaled desktop page.
    if not re.search(r'<meta\b[^>]*\bname\s*=\s*[\"\']?viewport\b', original, re.I):
        style = '<meta name="viewport" content="width=device-width,initial-scale=1">\n' + style
    closing_head = re.search(r"</head\s*>", original, flags=re.I)
    if closing_head:
        return original[:closing_head.start()] + style + original[closing_head.start():]
    opening_head = re.search(r"<head(?:\s[^>]*)?>", original, flags=re.I)
    if opening_head:
        pos = opening_head.end()
        return original[:pos] + '\n' + style + original[pos:]
    # Insert a head only for documents that don't have one. The original body stays intact.
    opening_html = re.search(r"<html(?:\s[^>]*)?>", original, flags=re.I)
    if opening_html:
        pos = opening_html.end()
        return original[:pos] + '\n<head>\n' + style + '</head>\n' + original[pos:]
    return '<head>\n' + style + '</head>\n' + original


def redesign_site(payload: dict[str, Any], *, use_ai: bool = True, require_ai: bool = False) -> dict[str, Any]:
    """Return EXACTLY Malak's required response: {'files': {original_path: complete_text}}."""
    if not isinstance(payload, dict) or payload.get("task") != "modernize_existing_website":
        raise WholeSiteError("Unsupported task")
    files = payload.get("files")
    if not isinstance(files, dict) or not files:
        raise WholeSiteError("Request must have a nonempty files object")
    if any(not isinstance(k, str) or not isinstance(v, str) for k, v in files.items()):
        raise WholeSiteError("Every file path and content must be text")
    if sum(len(v.encode("utf-8")) for v in files.values()) > MAX_INPUT_BYTES:
        raise WholeSiteError("HTML/CSS exceeds 1.2 MB")
    if any(not k.lower().endswith(EDITABLE_EXTENSIONS) for k in files):
        raise WholeSiteError("Only HTML and CSS files are supported")
    if not any(k.lower().endswith(HTML_EXTENSIONS) for k in files):
        raise WholeSiteError("No HTML pages found")
    plan, ai_used, reason = _choose_plan(files, use_ai)
    if require_ai and not ai_used:
        raise WholeSiteError('Local Gemma could not run. Open Ollama and ensure gemma3:1b is installed. ' + reason)
    css = _stylesheet(plan)
    updated = {path: _inject_css(content, css) if path.lower().endswith(HTML_EXTENSIONS) else content
               for path, content in files.items()}
    # Log only to the local server, never include diagnostic keys in the response contract.
    print(f"Whole-site plan: {plan}; AI used: {ai_used}; fallback: {reason}")
    return {"files": updated}


def make_offline_json(request_path: str, output_path: str, *, use_ai: bool = True) -> None:
    with open(request_path, encoding="utf-8") as source:
        payload = json.load(source)
    result = redesign_site(payload, use_ai=use_ai)
    with open(output_path, "w", encoding="utf-8") as dest:
        json.dump(result, dest, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate Malak-compatible whole-site AI JSON")
    parser.add_argument("request_json", help="JSON request conforming to TEAM_AI_INTERFACE.md")
    parser.add_argument("output_json", help="AI response JSON for Streamlit's Import team AI JSON")
    parser.add_argument("--no-ai", action="store_true", help="Use deterministic ocean/cards plan")
    args = parser.parse_args()
    make_offline_json(args.request_json, args.output_json, use_ai=not args.no_ai)
    print("Saved:", args.output_json)
