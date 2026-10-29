
from pathlib import Path
from ai_engine import generate_redesign

website_data = {
    "url": None,
    "year": None,
    "content": {
        "title": "Old Portfolio",
        "html": """
        <h1>Old Portfolio</h1>

        <p>
        I am a student interested in programming.
        </p>

        <h2>Projects</h2>
        <p>
        My projects include a personal blog.
        </p>
        """,
        "text": (
            "I am a student interested in programming. "
            "My projects include a personal blog."
        )
    },
    "analysis": {}
}

result = generate_redesign(website_data)

print("STATUS:", result["status"])
print("MESSAGE:", result["message"])

if result["status"] == "success":

    html = result["html"]

    Path("redesigned_website.html").write_text(
        html,
        encoding="utf-8"
    )

    print("HTML generated successfully!")

    print(
        "Original content preserved:",
        "I am a student interested in programming."
        in html
    )

    print(
        "Projects preserved:",
        "My projects include a personal blog."
        in html
    )
else:
    print("Redesign failed.")
