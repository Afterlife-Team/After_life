
from io import BytesIO
from zipfile import ZipFile

from analyzer import analyze_zip


def make_zip(files):
    buffer = BytesIO()

    with ZipFile(buffer, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)

    return buffer.getvalue()


def test_broken_link():
    data = make_zip({
        "index.html": '<a href="missing.html">Missing</a>'
    })

    result = analyze_zip(data)

    assert result["summary"]["broken_links_count"] == 1


def test_valid_link():
    data = make_zip({
        "index.html": '<a href="about.html">About</a>',
        "about.html": "<h1>About us</h1>"
    })

    result = analyze_zip(data)

    assert result["summary"]["broken_links_count"] == 0


def test_missing_image():
    data = make_zip({
        "index.html": '<img src="images/logo.png">'
    })

    result = analyze_zip(data)

    assert result["summary"]["missing_assets_count"] == 1


import pytest


def test_relative_link():
    data = make_zip({
        "index.html": '<a href="pages/about.html">About</a>',
        "pages/about.html": "<h1>About</h1>"
    })

    result = analyze_zip(data)

    assert result["summary"]["broken_links_count"] == 0


def test_parent_directory_link():
    data = make_zip({
        "pages/about.html": '<a href="../index.html">Home</a>',
        "index.html": "<h1>Home</h1>"
    })

    result = analyze_zip(data)

    assert result["summary"]["broken_links_count"] == 0


def test_external_link():
    data = make_zip({
        "index.html": '<a href="https://example.com">External</a>'
    })

    result = analyze_zip(data)

    assert result["summary"]["broken_links_count"] == 0


def test_unsafe_zip_path():
    data = make_zip({
        "../outside.html": "<h1>Unsafe</h1>"
    })

    with pytest.raises(ValueError):
        analyze_zip(data)
