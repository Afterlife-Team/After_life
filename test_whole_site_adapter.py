import unittest
from bs4 import BeautifulSoup
from whole_site_adapter import redesign_site, WholeSiteError


class WholeSiteTests(unittest.TestCase):
    def setUp(self):
        self.pages = {
            "index.html": '<!doctype html><html><head><title>Portfolio</title><script>let x=1;</script></head><body><header><h1>Hi Rana</h1></header><main><p>Original paragraph!</p><a href="about.html">About</a><img src="images/logo.png" alt="Logo"></main></body></html>',
            "about.html": '<html><body><h1>About</h1><p>Contact me now.</p><a href="index.html">Home</a></body></html>',
            "css/style.css": "body { color: black; }",
        }
        self.payload = {"task": "modernize_existing_website", "homepage": "index.html", "files": self.pages, "assets": ["images/logo.png"]}

    def test_preserve_every_page_content_refs_and_scripts(self):
        result = redesign_site(self.payload, use_ai=False)["files"]
        self.assertEqual(set(result), set(self.pages))
        self.assertEqual(result["css/style.css"], self.pages["css/style.css"])
        for name in ("index.html", "about.html"):
            old, new = BeautifulSoup(self.pages[name], "html.parser"), BeautifulSoup(result[name], "html.parser")
            for soup in (old, new):
                for tag in soup(["head", "script", "style", "noscript"]):
                    tag.decompose()
            self.assertEqual(old.get_text(" ", strip=True), new.get_text(" ", strip=True))
            self.assertIn('afterlife-whole-site-style', result[name])
        self.assertIn('<script>let x=1;</script>', result["index.html"])
        self.assertIn('href="about.html"', result["index.html"])
        self.assertIn('src="images/logo.png"', result["index.html"])

    def test_shared_styles(self):
        result = redesign_site(self.payload, use_ai=False)["files"]
        marker = '<style id="afterlife-whole-site-style">\n'
        self.assertEqual(result['index.html'].split(marker)[1].split('</style>')[0], result['about.html'].split(marker)[1].split('</style>')[0])

    def test_reject_invalid_input(self):
        with self.assertRaises(WholeSiteError):
            redesign_site({"task": "recover_missing_pages", "files": self.pages}, use_ai=False)


if __name__ == "__main__":
    unittest.main()
