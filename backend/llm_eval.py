import json
from typing import Any, Dict, Optional

import httpx

from .config import AppConfig
from .models import EvaluationResponse


SYSTEM_RUBRIC = (
    "You are an expert evaluator of question quality for eliciting useful LLM answers. "
    "Rate exactly these 4 attributes, each as 0=needs work, 1=okay, 2=strong: "
    "Clarity (single direct question), Specificity (topic/audience/numbers/timeframe), Context (essential background), "
    "Constraints & Format (length, tone, structure such as bullets/table/JSON). "
    "Compute score = (sum of the four) * 12.5, then map to label: good (>=75), ok (45-74), bad (<45). "
    "Return strict JSON: label, score (0-100), summary, subscores (array of {name, score:0-2, comment}), feedback (array of strings), suggestions (array of {title, text}), improved_prompt (string). "
    "For improved_prompt, output ONE rewritten question/instruction (no preface, no meta, no follow-up questions)."
)


def _build_user_prompt(prompt: str, goal: Optional[str]) -> str:
    return (
        "Evaluate and improve the QUESTION below using the 4-attribute rubric.\n\n"
        f"Question:\n{prompt}\n\n"
        f"Intended goal/use (optional): {goal or 'None'}\n\n"
        "Provide concise feedback and suggestions, and return a single rewritten improved question in improved_prompt."
    )


async def evaluate_with_ollama(prompt: str, goal: Optional[str], cfg: AppConfig) -> Optional[EvaluationResponse]:
    if not cfg.ollama.enabled:
        return None

    url = cfg.ollama.base_url.rstrip("/") + "/api/generate"
    headers = {"Content-Type": "application/json"}
    payload: Dict[str, Any] = {
        "model": cfg.ollama.model,
        "prompt": SYSTEM_RUBRIC + "\n\n" + _build_user_prompt(prompt, goal),
        "format": "json",
        "stream": False,
        "options": {"temperature": 0.2},
    }

    try:
        async with httpx.AsyncClient(timeout=cfg.ollama.timeout_sec) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return None

    # Ollama returns { response: "...json...", ... }
    text = data.get("response") if isinstance(data, dict) else None
    if not text:
        return None
    try:
        obj = json.loads(text)
    except Exception:
        return None

    try:
        # Validate/normalize into our model
        return EvaluationResponse(
            label=str(obj.get("label", "ok")).lower(),
            score=int(obj.get("score", 60)),
            summary=obj.get("summary", ""),
            subscores=obj.get("subscores", []),
            feedback=obj.get("feedback", []),
            suggestions=obj.get("suggestions", []),
            improved_prompt=obj.get("improved_prompt"),
        )
    except Exception:
        return None
