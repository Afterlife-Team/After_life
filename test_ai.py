
from ai_engine import summarize_website, reconstruct_page

sample_analysis = {
    "pages": [
        {
            "path": "index.html",
            "title": "Old Portfolio",
            "text": "Welcome to my personal portfolio. "
                    "I am a student interested in programming."
        },
        {
            "path": "projects.html",
            "title": "Projects",
            "text": "My projects include a personal blog."
        }
    ],
    "broken_links": [
        {
            "source": "index.html",
            "target": "about.html",
            "type": "link"
        }
    ],
    "missing_assets": [],
    "summary": {
        "total_pages": 2,
        "broken_links_count": 1,
        "missing_assets_count": 0
    }
}

result = summarize_website(sample_analysis)

print("\n=== AI WEBSITE SUMMARY ===\n")
print(result)




print("\n=== RECONSTRUCTED PAGE ===\n")

html = reconstruct_page(
    sample_analysis,
    "about.html"
)

print(html)

with open(
    "restored_about.html",
    "w",
    encoding="utf-8"
) as file:
    file.write(html)

print("\nSaved to restored_about.html")
