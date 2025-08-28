import json
from typing import Any, Dict, Optional

import httpx

from .config import AppConfig
from .models import EvaluationResponse


SYSTEM_RUBRIC = (
    "You are an expert evaluator of question quality for eliciting useful answers. "
    "Assess the user's QUESTION on how well it guides a helpful response. Focus on: "
    "Clarity (direct question), Specificity (topic/audience/numbers), Context (relevant background), "
    "Constraints & Format (length, tone, bullets/table/JSON), Scope & Feasibility (not overly broad), "
    "Neutrality (non-leading phrasing), Outcome Orientation (states intended use), and Clarification (invites clarifying questions). "
    "Return a strict JSON object with fields: label ('good'|'ok'|'bad'), score (0-100), summary, "
    "subscores (array of {name, score:0-5, comment}), feedback (array of strings), suggestions (array of {title, text}), "
    "improved_prompt (string with an improved QUESTION)."
)


def _build_user_prompt(prompt: str, goal: Optional[str]) -> str:
    return (
        "Evaluate the following QUESTION for its ability to elicit a high-quality answer.\n\n"
        f"Question:\n{prompt}\n\n"
        f"Intended goal/use (optional): {goal or 'None'}\n\n"
        "Scoring guidance:\n"
        "- 90-100: Exceptional; clear, specific, with context, feasible scope, and format.\n"
        "- 60-89: Good; one or two areas to tighten (e.g., context/specifics/format).\n"
        "- 0-59: Weak; vague or broad, lacks clarity, context, or constraints.\n"
        "Map the score to label: good (>=75), ok (45-74), bad (<45).\n"
        "Return an improved QUESTION that addresses the top gaps."
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
