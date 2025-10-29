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

Single Sign-On (SSO)
--------------------

This API supports OIDC SSO with Keycloak and ADFS. Configure credentials in `backend/config.json` and enable auth.

Example `backend/config.json` snippet:

{
  "auth": {
    "enabled": true,
    "session_secret": "change-me-to-a-long-random-value",
    "post_login_redirect": "file:///PATH/TO/repo/frontend/index.html",
    "default_provider": "keycloak",
    "providers": {
      "keycloak": {
        "issuer": "https://keycloak.example.com/realms/your-realm",
        "client_id": "your-client-id",
        "client_secret": "your-client-secret",
        "redirect_uri": "http://localhost:8000/auth/callback/keycloak"
      },
      "adfs": {
        "issuer": "https://adfs.example.com/adfs",
        "client_id": "your-client-id",
        "client_secret": "your-client-secret",
        "redirect_uri": "http://localhost:8000/auth/callback/adfs"
      }
    }
  }
}

Routes:
- GET `/auth/login?provider=keycloak|adfs` — redirect to IdP
- GET `/auth/callback/{provider}` — OIDC redirect handler
- GET `/auth/me` — current user (401 if not logged in)
- POST `/auth/logout` — clear session

Protection:
- When `auth.enabled` is true, the API requires login for `/api/*` and `/api/examples` endpoints. `/health` and `/auth/*` remain public.

CORS:
- If using cookies from a separate origin (including `file://`), set `allowed_origins` in `backend/config.json` to your frontend origin(s). For example:

  "allowed_origins": ["http://localhost:8000", "http://localhost:5173", "null"]

  Note: Browsers require a non-wildcard origin when `Access-Control-Allow-Credentials: true`.

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

Frontend Dev Server
-------------------

For local development with SSO cookies, serve the frontend on a local HTTP origin instead of opening the file directly.

1) Start the static server on 5173:

   python scripts/serve_frontend.py --port 5173

2) Ensure `allowed_origins` in `backend/config.json` includes `http://localhost:5173` when auth is enabled.

3) Open http://localhost:5173 in your browser.
