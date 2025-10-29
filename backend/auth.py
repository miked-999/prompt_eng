"""OIDC-based authentication for FastAPI (Keycloak, ADFS).

Provides login, callback, me, and logout endpoints and a dependency to protect
API routes. Uses Authlib's AsyncOAuth2Client with OIDC discovery.
"""

import secrets
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request
from starlette.responses import RedirectResponse, JSONResponse
from authlib.integrations.httpx_client import AsyncOAuth2Client

from .config import AppConfig, OIDCProvider


SESSION_USER_KEY = "user"
SESSION_STATE_KEY = "oauth_state"
SESSION_NONCE_KEY = "oauth_nonce"
SESSION_PROVIDER_KEY = "oauth_provider"


def _resolve_provider(cfg: AppConfig, name: Optional[str]) -> OIDCProvider:
    if not name:
        if cfg.auth.default_provider and cfg.auth.default_provider in cfg.auth.providers:
            return cfg.auth.providers[cfg.auth.default_provider]
        raise HTTPException(status_code=400, detail="No provider specified and no default configured")
    prov = cfg.auth.providers.get(name)
    if not prov:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {name}")
    return prov


async def _load_metadata(client: AsyncOAuth2Client, provider: OIDCProvider) -> Dict[str, Any]:
    if provider.discovery_url:
        resp = await client.get(provider.discovery_url)
    elif provider.issuer:
        url = provider.issuer.rstrip("/") + "/.well-known/openid-configuration"
        resp = await client.get(url)
    else:
        raise HTTPException(status_code=500, detail="Provider missing discovery_url or issuer")
    resp.raise_for_status()
    meta = resp.json()
    client.metadata = meta
    return meta


def _new_client(provider: OIDCProvider) -> AsyncOAuth2Client:
    return AsyncOAuth2Client(
        client_id=provider.client_id,
        client_secret=provider.client_secret,
        scope="openid email profile",
        redirect_uri=provider.redirect_uri or None,
    )


async def start_login(request: Request, cfg: AppConfig, provider_name: Optional[str]):
    if not cfg.auth.enabled:
        raise HTTPException(status_code=404, detail="Auth is disabled")

    provider = _resolve_provider(cfg, provider_name)
    client = _new_client(provider)
    meta = await _load_metadata(client, provider)
    auth_endpoint = meta.get("authorization_endpoint")
    if not auth_endpoint:
        raise HTTPException(status_code=500, detail="Provider missing authorization_endpoint")

    state = secrets.token_urlsafe(16)
    nonce = secrets.token_urlsafe(16)
    request.session[SESSION_STATE_KEY] = state
    request.session[SESSION_NONCE_KEY] = nonce
    request.session[SESSION_PROVIDER_KEY] = provider.name

    url, _ = client.create_authorization_url(auth_endpoint, state=state, nonce=nonce)
    return RedirectResponse(url, status_code=302)


async def handle_callback(request: Request, cfg: AppConfig, provider_name: str):
    if not cfg.auth.enabled:
        raise HTTPException(status_code=404, detail="Auth is disabled")

    state = request.query_params.get("state")
    code = request.query_params.get("code")
    expected_state = request.session.get(SESSION_STATE_KEY)
    nonce = request.session.get(SESSION_NONCE_KEY)
    session_provider = request.session.get(SESSION_PROVIDER_KEY)

    if not code:
        raise HTTPException(status_code=400, detail="Missing code")
    if not state or not expected_state or state != expected_state:
        raise HTTPException(status_code=400, detail="Invalid state")
    if not nonce:
        raise HTTPException(status_code=400, detail="Missing nonce")
    if session_provider and session_provider != provider_name:
        raise HTTPException(status_code=400, detail="Provider mismatch")

    provider = _resolve_provider(cfg, provider_name)
    client = _new_client(provider)
    meta = await _load_metadata(client, provider)

    token_endpoint = meta.get("token_endpoint")
    if not token_endpoint:
        raise HTTPException(status_code=500, detail="Provider missing token_endpoint")

    token = await client.fetch_token(
        token_endpoint,
        code=code,
        client_secret=provider.client_secret,
    )

    # Validate ID token and extract claims
    claims = await client.parse_id_token(token, nonce=nonce)

    user = {
        "sub": claims.get("sub"),
        "email": claims.get("email"),
        "name": claims.get("name") or claims.get("given_name"),
        "preferred_username": claims.get("preferred_username"),
        "provider": provider.name,
    }

    # Persist user session
    request.session[SESSION_USER_KEY] = user
    # Clear transient oauth values
    request.session.pop(SESSION_STATE_KEY, None)
    request.session.pop(SESSION_NONCE_KEY, None)
    request.session.pop(SESSION_PROVIDER_KEY, None)

    # Redirect to app (frontend)
    target = cfg.auth.post_login_redirect or "/"
    return RedirectResponse(target, status_code=302)


def current_user(request: Request) -> Optional[Dict[str, Any]]:
    return request.session.get(SESSION_USER_KEY)


def require_user(request: Request) -> Dict[str, Any]:
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


async def me(request: Request):
    user = current_user(request)
    if not user:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
    return user


async def logout(request: Request):
    request.session.clear()
    return JSONResponse(status_code=200, content={"ok": True})
