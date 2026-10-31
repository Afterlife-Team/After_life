
import pytest

from services.site_bundle import site_from_zip
from services.ai_bridge import apply_ai_changes, AIIntegrationError

import io
import zipfile


def test_ai_rejects_partial_text_removal():
    # Create a website with 10 distinct paragraphs.
    paragraphs = [
        f"<p>Important original content number {i} must remain unchanged.</p>"
        for i in range(10)
    ]

    original_html = (
        "<html><head><title>Original Website</title></head>"
        "<body>" + "".join(paragraphs) + "</body></html>"
    )

    # Package the original website as a ZIP.
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("index.html", original_html)

    original = site_from_zip(buffer.getvalue())

    # Simulate AI removing one original paragraph.
    redesigned_html = original_html.replace(
        paragraphs[5],
        ""
    ).replace(
        "<body>",
        '<body class="modern-design">'
    )

    # Content loss must be rejected.
    with pytest.raises(AIIntegrationError, match="visible text"):
        apply_ai_changes(
            original,
            {"index.html": redesigned_html}
        )

def test_duplicate_text_must_not_be_lost():
    original = "Important original notice. Important original notice."
    redesigned = "Important original notice."

    from services.ai_bridge import _content_preserved

    assert not _content_preserved(original, redesigned)
def test_duplicate_text_not_counted_inside_longer_text():
    from services.ai_bridge import _content_preserved

    original = "Important notice. Important notice."
    redesigned = "Important notice is shown here. Important noticeboard."

    assert not _content_preserved(original, redesigned)
    
def test_preserves_text_with_added_header():
    from services.ai_bridge import _content_preserved

    original = (
        "About Us We are an independent technology store founded years ago."
    )

    redesigned = (
        "Real Old Store About Contact "
        "About Us We are an independent technology store founded years ago."
    )

    assert _content_preserved(original, redesigned)
