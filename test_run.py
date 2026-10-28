
from analyzer import extract_content

html = """
<html>
<head>
    <title>Old Portfolio</title>
</head>
<body>
    <h1>Welcome to my website</h1>
    <h2>About My Work</h2>

    <p>I love programming and AI.</p>
    <p>This is my old portfolio.</p>

    <a href="projects.html">Projects</a>
    <a href="about.html">About Me</a>

    <img src="images/logo.png" alt="My Logo">
</body>
</html>
"""

result = extract_content(html)

print("Title:", result["title"])
print("Headings:", result["headings"])
print("Paragraphs:", result["paragraphs"])
print("Links:", result["links"])
print("Images:", result["images"])
