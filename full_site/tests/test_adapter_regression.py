"""Regression coverage for the whole-site adapter / Malak bridge boundary."""
import importlib.util
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from services.ai_bridge import apply_ai_changes, AIIntegrationError
from services.site_bundle import site_from_zip, to_zip
from services.preview import preview_page

spec = importlib.util.spec_from_file_location('review_adapter', Path(__file__).parents[2] / 'whole_site_adapter.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def sample():
    path = Path(__file__).parents[1] / 'examples/sample_website_404_afterlife.zip'
    return site_from_zip(path.read_bytes())


def payload(site):
    return {'task': 'modernize_existing_website', 'files': {
        p: text.decode('utf-8') for p, text in site.files.items()
        if p.lower().endswith(('.html', '.htm', '.css'))}}


@pytest.mark.parametrize('theme', sorted(adapter.THEMES))
@pytest.mark.parametrize('layout', sorted(adapter.LAYOUTS))
def test_adapter_bridge_export_preserves_original_dom(monkeypatch, theme, layout):
    site = sample()
    monkeypatch.setattr(adapter, '_choose_plan', lambda *a: ({'theme': theme, 'layout': layout}, True, ''))
    response = adapter.redesign_site(payload(site))
    assert set(response) == {'files'}
    revised = apply_ai_changes(site, response['files'])
    exported = site_from_zip(to_zip(revised))
    assert set(exported.files) == set(site.files)
    shared = []
    for page in site.pages:
        before = BeautifulSoup(site.files[page], 'html.parser')
        after = BeautifulSoup(exported.files[page], 'html.parser')
        assert str(after.body) == str(before.body)
        assert len(after.select('meta[name=viewport]')) == 1
        shared.append(after.select_one('#afterlife-whole-site-style').string)
        assert "script-src 'none'" in preview_page(revised, page)
    assert len(set(shared)) == 1
    for path in set(site.files) - set(site.pages):
        assert exported.files[path] == site.files[path]


def test_ollama_schema_single_call_and_fallback(monkeypatch):
    import ollama
    calls = []
    def chat(**kwargs):
        calls.append(kwargs)
        return {'message': {'content': '{"theme":" Forest ","layout":"Minimal"}'}}
    monkeypatch.setattr(ollama, 'chat', chat)
    plan, used, reason = adapter._choose_plan(payload(sample())['files'], True)
    assert plan == {'theme': 'forest', 'layout': 'minimal'} and used and not reason
    assert len(calls) == 1 and calls[0]['model'] == 'gemma3:1b'
    assert calls[0]['format']['additionalProperties'] is False
    monkeypatch.setattr(ollama, 'chat', lambda **kw: {'message': {'content': 'invalid'}})
    plan, used, reason = adapter._choose_plan(payload(sample())['files'], True)
    assert not used and reason and plan['theme'] == 'ocean'


def test_existing_viewport_and_form_attributes_untouched():
    html = '<html><head><meta name="viewport" content="width=device-width,initial-scale=2"></head><body><form action="search.html" method="get"><input name="q"><button>Search</button></form></body></html>'
    result = adapter._inject_css(html, adapter._stylesheet({'theme': 'ocean', 'layout': 'cards'}))
    assert result.count('name="viewport"') == 1
    assert html.split('<body>')[1] == result.split('<body>')[1]


def test_validator_still_rejects_missing_page_and_changed_link():
    site = sample()
    changes = adapter.redesign_site(payload(site), use_ai=False)['files']
    incomplete = dict(changes)
    incomplete.pop(site.pages[0])
    with pytest.raises(AIIntegrationError):
        apply_ai_changes(site, incomplete)
    home = site.homepage
    changes[home] = changes[home].replace('href="about.html"', 'href="missing.html"')
    with pytest.raises(AIIntegrationError):
        apply_ai_changes(site, changes)
