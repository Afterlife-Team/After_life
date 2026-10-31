from ai_engine import generate_redesign
from html_validator import validate_html
from html_renderer import render_website


def test_render_navigation_and_theme():
    html = render_website({'title': 'Old Portfolio', 'theme': 'forest', 'layout': 'editorial',
        'sections': [{'heading': 'Welcome', 'text': ''}], 'navigation': [
        {'label': 'Projects', 'href': 'projects.html', 'status': 'working'},
        {'label': 'About Me', 'href': 'about.html', 'status': 'missing'}]})
    assert 'href="projects.html"' in html
    assert 'About Me - Missing Page' in html
    assert 'layout-editorial' in html
    assert validate_html(html)['valid'], validate_html(html)['errors']


def test_ai_plan_applied(monkeypatch):
    import ai_engine
    monkeypatch.setattr(ai_engine, 'plan_design', lambda sections, analysis: {
        'theme': 'sunset', 'layout': 'minimal', 'ordered_ids': list(range(len(sections)))})
    result = generate_redesign({'content': {'title': 'Portfolio', 'html': '<h2>Projects</h2><p>Blog</p>'}})
    assert result['status'] == 'success', result['message']
    assert result['ai_used'] is True
    assert result['theme'] == 'sunset'
    assert 'layout-minimal' in result['html']
    assert 'Blog' in result['html']


def test_fallback_is_reported(monkeypatch):
    import ai_engine
    def offline(*args):
        raise RuntimeError('offline')
    monkeypatch.setattr(ai_engine, 'plan_design', offline)
    result = generate_redesign({'content': {'title': 'Portfolio', 'html': '<h2>Welcome</h2>'}})
    assert result['status'] == 'success', result['message']
    assert result['ai_used'] is False
    assert 'offline' in result['fallback_reason']
