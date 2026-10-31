"""Run the existing whole-site adapter locally, then use Malak's validator."""
import importlib.util
from pathlib import Path

from services.ai_bridge import apply_ai_changes, AIIntegrationError
from services.encoding import decode_html
from services.site_bundle import SiteBundle


def _load_adapter():
    path = Path(__file__).resolve().parents[2] / 'whole_site_adapter.py'
    spec = importlib.util.spec_from_file_location('afterlife_local_adapter', path)
    if spec is None or spec.loader is None:
        raise AIIntegrationError('The local whole-site adapter is unavailable.')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def redesign_with_local_gemma(original: SiteBundle) -> SiteBundle:
    editable = {p: decode_html(raw) for p, raw in original.files.items()
                if p.lower().endswith(('.html', '.htm', '.css'))}
    payload = {'task': 'modernize_existing_website', 'homepage': original.homepage,
               'files': editable, 'assets': sorted(set(original.files) - set(editable))}
    try:
        adapter = _load_adapter()
        response = adapter.redesign_site(payload, use_ai=True, require_ai=True)
    except (ImportError, OSError, ValueError) as exc:
        raise AIIntegrationError(str(exc)) from exc
    # Keep the same response contract and validation boundary as imported/HTTP AI.
    if not isinstance(response, dict) or not isinstance(response.get('files'), dict):
        raise AIIntegrationError('Local Gemma returned an invalid files response.')
    return apply_ai_changes(original, response['files'])
