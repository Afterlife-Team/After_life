
from analyzer import check_broken_links

result = check_broken_links("sample_site")

print("Broken Links:", result["broken_links"])
print("Missing Images:", result["missing_images"])
