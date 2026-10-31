from services.reconstruct import extract_content, build_reconstruction

def test_extraction_and_escaping():
    data = extract_content("<title>Demo</title><h1>Hi</h1><p>Some useful archived content here.</p><script>alert(1)</script>")
    assert data["title"] == "Demo"
    assert data["headings"] == ["Hi"]
    output = build_reconstruction({"title": "<script>x</script>", "headings": ['<img src=x onerror=alert(1)>'], "paragraphs": [], "links": []}, "https://example.com", "2015")
    assert "&lt;script&gt;" in output
    assert "<img src=x" not in output
    assert "default-src 'none'" in output
