Prompt Engineering Trainer (Python + Vue)
=========================================

A simple web app to practice and gamify prompt engineering:
- Evaluate your prompts with heuristic scoring and suggestions
- Take a quiz to identify good/ok/bad prompts and see rationales

Stack
-----
- Backend: FastAPI (Python)
- Frontend: Vue 3 via CDN (no build step)

Run Backend
-----------
1) Create a virtual env and install deps:

   python -m venv .venv
   source .venv/bin/activate
   pip install -r backend/requirements.txt

2) Start the API on port 8000:

   uvicorn backend.app:app --reload

Run Frontend
------------
Option A (quick): open `frontend/index.html` directly in a browser.

Option B (recommended for SSO cookies): run a tiny static server on port 5173 and browse to it.

  python scripts/serve_frontend.py --port 5173

Ensure the backend CORS `allowed_origins` includes `http://localhost:5173` if auth is enabled.

API Endpoints
-------------
- GET `/health` — status check
- POST `/api/evaluate` — body `{ prompt: string, goal?: string }`
- GET `/api/quiz?limit=10` — returns quiz items
- POST `/api/quiz/submit` — body `{ answers: [{ item_id, label }] }`

Notes
-----
- The scoring is heuristic-based, focusing on role, goal clarity, context, constraints, examples, evaluation criteria, structure, and uncertainty handling.
- Improve it by adjusting weights or adding domain-specific checks.

LLM Evaluation (Ollama)
-----------------------
- You can enable LLM-backed evaluation via Ollama by editing `backend/config.json`:

  {
    "ollama": {
      "enabled": true,
      "base_url": "http://localhost:11434",
      "model": "llama3.1",
      "timeout_sec": 20
    }
  }

- Make sure Ollama is running and the model is available:

  - Install/start Ollama: https://ollama.com/
  - Pull a model, for example: `ollama pull llama3.1`
  - Start the server (usually auto): `ollama serve`

- The API tries LLM evaluation first; on failure or if disabled, it falls back to the built-in heuristic.
