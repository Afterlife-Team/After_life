
from html_renderer import render_website
from html_validator import validate_html

data = {
    "title": "Old Portfolio",
    "subtitle": "Student interested in programming",
    "sections": [
        {
            "heading": "Projects",
            "text": "My projects include a personal blog."
        },
        {
            "heading": "About",
            "text": "I am a student interested in programming."
        }
    ]
}

html = render_website(data)

result = validate_html(html)

print("VALID:", result["valid"])
print("ERRORS:", result["errors"])

with open("new_website.html", "w", encoding="utf-8") as f:
    f.write(html)

