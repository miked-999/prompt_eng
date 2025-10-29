import json
import os
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.json"


@dataclass
class OllamaConfig:
    enabled: bool = False
    base_url: str = "http://localhost:11434"
    model: str = "llama3.1"
    timeout_sec: int = 20


@dataclass
class AppConfig:
    ollama: 'OllamaConfig'
    auth: 'AuthConfig'
    allowed_origins: list[str] = field(default_factory=lambda: ["*"])


@dataclass
class OIDCProvider:
    name: str
    issuer: str | None = None
    discovery_url: str | None = None
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = ""


@dataclass
class AuthConfig:
    enabled: bool = False
    session_secret: str = "change-me"
    default_provider: str | None = None
    providers: dict[str, OIDCProvider] = field(default_factory=dict)
    post_login_redirect: str = "/"


def load_config() -> AppConfig:
    path = os.getenv("PROMPT_TRAINER_CONFIG", str(DEFAULT_CONFIG_PATH))
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return AppConfig(
            ollama=OllamaConfig(),
            auth=AuthConfig(),
        )

    ol = data.get("ollama", {}) if isinstance(data, dict) else {}
    # Auth config (optional)
    au_raw = data.get("auth", {}) if isinstance(data, dict) else {}
    allowed_origins = data.get("allowed_origins") or ["*"]
    providers: dict[str, OIDCProvider] = {}
    for name, pv in (au_raw.get("providers", {}) or {}).items():
        providers[name] = OIDCProvider(
            name=name,
            issuer=pv.get("issuer"),
            discovery_url=pv.get("discovery_url"),
            client_id=str(pv.get("client_id", "")),
            client_secret=str(pv.get("client_secret", "")),
            redirect_uri=str(pv.get("redirect_uri", "")),
        )

    return AppConfig(
        ollama=OllamaConfig(
            enabled=bool(ol.get("enabled", False)),
            base_url=str(ol.get("base_url", "http://localhost:11434")),
            model=str(ol.get("model", "llama3.1")),
            timeout_sec=int(ol.get("timeout_sec", 20)),
        ),
        auth=AuthConfig(
            enabled=bool(au_raw.get("enabled", False)),
            session_secret=str(au_raw.get("session_secret", "change-me")),
            default_provider=(au_raw.get("default_provider") or None),
            providers=providers,
            post_login_redirect=str(au_raw.get("post_login_redirect", "/")),
        ),
        allowed_origins=[str(o) for o in allowed_origins],
    )
