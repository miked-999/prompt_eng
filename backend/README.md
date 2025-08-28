Prompt Engineering Trainer API
==============================

Quickstart
----------

1) Create a virtual env and install deps:

   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

2) Run the API:

   uvicorn backend.app:app --reload

Endpoints
---------

- GET /health — service health
- POST /api/evaluate — body `{ prompt: string, goal?: string }`
- GET /api/quiz?limit=10 — fetch quiz items
- POST /api/quiz/submit — body `{ answers: [{ item_id, label }] }`
- GET /api/examples — curated BAD/OK/GOOD examples

API Docs
--------
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

OpenAPI metadata includes route summaries, descriptions, and schema examples.
