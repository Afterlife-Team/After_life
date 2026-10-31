from pathlib import Path
import importlib.util
import pytest
from streamlit.testing.v1 import AppTest
from services.site_bundle import site_from_zip, to_zip
from services.ai_bridge import AIIntegrationError
from services import local_ai


def adapter():
    return local_ai._load_adapter()


def sample():
    return site_from_zip((Path(__file__).parents[1]/'examples/sample_website_404_afterlife.zip').read_bytes())


def test_direct_local_success_preserves_assets(monkeypatch):
    model = adapter()
    monkeypatch.setattr(model, '_choose_plan', lambda *a: ({'theme':'forest','layout':'cards'},True,''))
    monkeypatch.setattr(local_ai, '_load_adapter', lambda: model)
    original = sample()
    revised = local_ai.redesign_with_local_gemma(original)
    assert site_from_zip(to_zip(revised)).files == revised.files
    assert revised.pages == original.pages
    for path in original.files:
        if path not in original.pages:
            assert original.files[path] == revised.files[path]


def test_unavailable_model_is_error_not_fake_ai(monkeypatch):
    model = adapter()
    monkeypatch.setattr(model,'_choose_plan',lambda *a: ({'theme':'ocean','layout':'cards'},False,'offline'))
    monkeypatch.setattr(local_ai,'_load_adapter',lambda: model)
    with pytest.raises(AIIntegrationError,match='Ollama'):
        local_ai.redesign_with_local_gemma(sample())


def test_local_result_still_passes_validator(monkeypatch):
    class Broken:
        def redesign_site(self, payload, **kwargs):
            assert kwargs == {'use_ai':True,'require_ai':True}
            return {'files': {'index.html':'<html><body>Lost content</body></html>'}}
    monkeypatch.setattr(local_ai,'_load_adapter',lambda: Broken())
    with pytest.raises(AIIntegrationError):
        local_ai.redesign_with_local_gemma(sample())


def test_local_ui_default_needs_only_zip():
    app=AppTest.from_file(str(Path(__file__).parents[1]/'app.py')).run(timeout=20)
    assert not app.exception
    assert len(app.radio) == 2
    assert app.radio[1].value == 'Local Gemma (Ollama)'
    assert app.radio[0].value == 'Upload ZIP'
    assert not app.warning
    assert len(app.get('file_uploader')) == 1
    app.button[0].click().run()
    assert not app.exception
    assert any('Upload a ZIP' in e.value for e in app.error)
