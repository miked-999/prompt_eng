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

- GET /health
- POST /api/evaluate { prompt, goal? }
- GET /api/quiz?limit=10
- POST /api/quiz/submit { answers: [{ item_id, label }] }

