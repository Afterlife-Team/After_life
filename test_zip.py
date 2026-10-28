
from pathlib import Path
from analyzer import analyze_zip
import json

zip_data = Path("sample_site.zip").read_bytes()

result = analyze_zip(zip_data)

print(json.dumps(result["summary"], indent=4))
print("\nBROKEN LINKS:")
print(json.dumps(result["broken_links"], indent=4))

print("\nMISSING ASSETS:")
print(json.dumps(result["missing_assets"], indent=4))
 
# Save analysis results as JSON
output_file = Path("analysis_result.json")

output_file.write_text(
    json.dumps(result, indent=4, ensure_ascii=False),
    encoding="utf-8"
)

print("\nAnalysis saved to:", output_file)
print("\nAI INPUT PREVIEW:")

ai_input = {
    "pages": result["pages"],
    "broken_links": result["broken_links"],
    "missing_assets": result["missing_assets"]
}

print(json.dumps(ai_input, indent=4, ensure_ascii=False))

print("\nAVAILABLE MISSING PAGES:")

missing_pages = [
    item["target"]
    for item in result["broken_links"]
    if item["target"].lower().endswith((".html", ".htm"))
]

print(missing_pages)
