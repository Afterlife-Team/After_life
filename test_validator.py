
from pathlib import Path

from html_validator import validate_html


def check(name, html, expected_valid):
    result = validate_html(html)

    print(f"\n=== {name} ===")
    print("VALID:", result["valid"])
    print("ERRORS:", result["errors"])

    assert result["valid"] == expected_valid, (
        f"Unexpected result for {name}"
    )


# Test 1: Valid basic HTML
valid_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport"
          content="width=device-width, initial-scale=1">
    <title>Test</title>
    <style>
        body { color: #222; }
    </style>
</head>
<body>
    <main>
        <h1>Welcome</h1>
        <p>Test content</p>
    </main>
</body>
</html>
"""

check("Valid HTML", valid_html, True)


# Test 2: JavaScript must be rejected
script_html = """
<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
    <script>alert('test')</script>
</body>
</html>
"""

check("Forbidden Script", script_html, False)


# Test 3: Invalid structure
broken_html = """
<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
    <section><h1>Title</h1></section>
    </section>
</body>
</html>
"""

check("Broken HTML Structure", broken_html, False)


# Test 4: External CSS URL
unsafe_css = """
<!DOCTYPE html>
<html>
<head>
    <title>Test</title>
    <style>
        body {
            background: url(https://example.com/image.png);
        }
    </style>
</head>
<body>
    <h1>Hello</h1>
</body>
</html>
"""

check("External CSS Resource", unsafe_css, False)


# Test 5: Check generated HTML if available
generated = Path("redesigned_website.html")

if generated.exists():
    html = generated.read_text(encoding="utf-8")
    result = validate_html(html)

    print("\n=== GENERATED GEMMA HTML ===")
    print("VALID:", result["valid"])
    print("ERRORS:", result["errors"])
else:
    print("\nNo generated website file found.")
