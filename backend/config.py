import json
import os
from dataclasses import dataclass
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
    ollama: OllamaConfig


def load_config() -> AppConfig:
    path = os.getenv("PROMPT_TRAINER_CONFIG", str(DEFAULT_CONFIG_PATH))
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return AppConfig(ollama=OllamaConfig())

    ol = data.get("ollama", {}) if isinstance(data, dict) else {}
    return AppConfig(
        ollama=OllamaConfig(
            enabled=bool(ol.get("enabled", False)),
            base_url=str(ol.get("base_url", "http://localhost:11434")),
            model=str(ol.get("model", "llama3.1")),
            timeout_sec=int(ol.get("timeout_sec", 20)),
        )
    )

