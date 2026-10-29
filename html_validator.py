
import re
from bs4 import BeautifulSoup
from html5lib.html5parser import HTMLParser


ALLOWED_TAGS = {
    "html", "head", "body", "title", "meta",
    "style", "header", "footer", "main", "nav",
    "section", "article", "aside", "div",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "span", "strong", "em", "b", "i",
    "ul", "ol", "li", "br", "hr",
    "blockquote", "small"
}

GLOBAL_ATTRIBUTES = {
    "class", "id", "aria-label", "role"
}

ALLOWED_ATTRIBUTES = {
    "html": {"lang"},
    "meta": {"charset", "name", "content"}
}

DANGEROUS_CSS = re.compile(
    r"@import|@font-face|@namespace|"
    r"url\s*\(|expression\s*\(|"
    r"image-set\s*\(|-moz-binding|"
    r"behavior\s*:",
    re.IGNORECASE
)

MAX_HTML_LENGTH = 100_000


def validate_html(html):
    errors = []

    if not isinstance(html, str) or not html.strip():
        return {
            "valid": False,
            "errors": ["HTML is empty"]
        }

    if len(html) > MAX_HTML_LENGTH:
        errors.append("HTML exceeds maximum length")

    if not re.search(
        r"^\s*<!doctype\s+html\s*>",
        html,
        flags=re.IGNORECASE
    ):
        errors.append("Missing HTML5 doctype")

    if not re.search(r"<html\b", html, re.I):
        errors.append("Missing html tag")

    if not re.search(r"<body\b", html, re.I):
        errors.append("Missing body tag")

    if not re.search(r"</html\s*>", html, re.I):
        errors.append("Missing closing html tag")

    # Check HTML structure
    parser = HTMLParser(strict=False)

    try:
        parser.parse(html)

        for position, code, details in parser.errors:
            line, column = position

            errors.append(
                f"HTML structure error "
                f"at {line}:{column}: {code}"
            )

    except Exception as error:
        errors.append(
            "HTML parsing failed: "
            + type(error).__name__
        )

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(True):
        name = tag.name.lower()

        if name not in ALLOWED_TAGS:
            errors.append(
                f"Forbidden tag: {name}"
            )
            continue

        # Only allow required metadata
        if name == "meta":
            charset = tag.get("charset")

            meta_name = str(
                tag.get("name", "")
            ).lower()

            meta_content = str(
                tag.get("content", "")
            ).strip()

            is_charset = (
                str(charset).lower() == "utf-8"
                and set(tag.attrs) == {"charset"}
            )

            is_viewport = (
                meta_name == "viewport"
                and meta_content ==
                "width=device-width, initial-scale=1"
                and set(tag.attrs) ==
                {"name", "content"}
            )

            if not (is_charset or is_viewport):
                errors.append(
                    "Disallowed meta element"
                )

        allowed_attributes = (
            GLOBAL_ATTRIBUTES
            | ALLOWED_ATTRIBUTES.get(name, set())
        )

        for attr, value in tag.attrs.items():
            if attr.lower() not in allowed_attributes:
                errors.append(
                    f"Forbidden attribute: {name}.{attr}"
                )

        if name == "style":
            css = tag.get_text()

            if DANGEROUS_CSS.search(css):
                errors.append(
                    "Disallowed CSS feature detected"
                )

    return {
        "valid": len(errors) == 0,
        "errors": list(dict.fromkeys(errors))
    }
