"""Start this project's Streamlit UI using the already verified local runtime."""
from pathlib import Path
import sys

root = Path(__file__).resolve().parent
deps = Path.home() / 'Documents/ChatGPT/Hacathon/.review-deps'
if deps.is_dir():
    sys.path.insert(0, str(deps))
sys.path.insert(0, str(root / 'full_site'))
try:
    from streamlit.web import cli
    import ollama
except ImportError as exc:
    raise SystemExit(f'Missing dependency: {exc}. Install full_site/requirements.txt with a working Python.')
sys.argv = ['streamlit', 'run', str(root/'full_site/app.py'),
            '--global.developmentMode=false', '--server.address=127.0.0.1',
            '--server.port=8501', '--server.headless=true', '--browser.gatherUsageStats=false']
cli.main()
