# 🤖 AI Development — 404 Afterlife

**Branch:** `feature/ai`  
**Developer:** Rana Mahmoud

## My Contributions

- Developed the AI redesign engine using **Gemma 3 1B** and **Ollama**.
- Built the whole-site adapter to apply consistent designs across multiple HTML pages.
- Implemented structured AI design selection and responsive CSS generation.
- Integrated the local AI workflow with the application's website processing system.
- Added AI output validation and content-preservation checks.
- Developed and tested AI redesign and integration components.

## Main Files

- `whole_site_adapter.py` — Whole-site AI adapter.
- `ai_engine.py` — AI redesign engine.
- `html_renderer.py` — HTML rendering.
- `html_validator.py` — Output validation.
- `full_site/services/local_ai.py` — Local Gemma integration.
- `test_whole_site_adapter.py` — Adapter tests.
- `full_site/tests/test_local_ai.py` — Local AI tests.

## Technologies

Python · Gemma 3 1B · Ollama · BeautifulSoup · HTML/CSS · JSON

## Testing

```bash
python -m unittest test_whole_site_adapter
```

Full integration testing requires the application's UI/backend components.

---

**Main Project:** [404 Afterlife](https://github.com/Afterlife-Team/After_life)
