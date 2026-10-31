"""Smoke checks for the executable UI and HTTP AI boundary (no external calls)."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from streamlit.testing.v1 import AppTest
from services.ai_bridge import request_ai_redesign
from services.site_bundle import site_from_zip, to_zip
from services.redesign import modernize_site
from services.preview import preview_page


def test_sample_zip_workflow():
    sample = Path(__file__).parents[1] / 'examples/sample_website_404_afterlife.zip'
    original = site_from_zip(sample.read_bytes())
    revised = modernize_site(original)
    exported = site_from_zip(to_zip(revised))
    assert exported.pages == original.pages
    for page in original.pages:
        assert "script-src 'none'" in preview_page(revised, page)
    for path, data in original.files.items():
        if path not in original.pages:
            assert exported.files[path] == data


def test_team_http_contract():
    sample = Path(__file__).parents[1] / 'examples/sample_website_404_afterlife.zip'
    original = site_from_zip(sample.read_bytes())
    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            received.append(payload)
            files = {p: text + '\n<!-- team integration test -->' for p, text in payload['files'].items() if p in original.pages}
            body = json.dumps({'files': files}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        revised = request_ai_redesign(original, endpoint=f'http://127.0.0.1:{server.server_port}/redesign')
        assert received[0]['task'] == 'modernize_existing_website'
        assert revised.pages == original.pages
        assert revised.files[original.homepage] != original.files[original.homepage]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_streamlit_initial_and_url_validation(monkeypatch):
    monkeypatch.delenv('AFTERLIFE_AI_ENDPOINT', raising=False)
    app = AppTest.from_file(str(Path(__file__).parents[1] / 'app.py')).run(timeout=20)
    assert not app.exception
    app.button[0].click().run()
    assert not app.exception
    assert any('Upload a ZIP' in e.value for e in app.error)
    app.radio[0].set_value('Recover from URL').run()
    app.text_input[0].set_value('http://localhost/')
    app.button[0].click().run()
    assert not app.exception
    assert any('Local hosts' in e.value for e in app.error)
