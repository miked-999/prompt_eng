import json
from typing import Any, Dict, Optional

import httpx

from .config import AppConfig
from .models import EvaluationResponse


SYSTEM_RUBRIC = (
    "You are an expert evaluator of prompt engineering quality. "
    "Assess prompts based on: Role/Persona, Goal clarity, Context, Constraints "
    "(length, tone, format), Examples (few-shot), Evaluation/acceptance criteria, "
    "Structure of expected output, and Uncertainty handling (clarifying questions, cite sources). "
    "Return a strict JSON object with fields: label ('good'|'ok'|'bad'), score (0-100), "
    "summary, subscores (array of {name, score:0-5, comment}), feedback (array of strings), "
    "suggestions (array of {title, text}), improved_prompt (string)."
)


def _build_user_prompt(prompt: str, goal: Optional[str]) -> str:
    return (
        "Evaluate the following prompt for quality.\n\n"
        f"Prompt:\n{prompt}\n\n"
        f"Goal (optional): {goal or 'None'}\n\n"
        "Scoring guidance:\n"
        "- 90-100: Exceptional; explicit role, clear goal, rich context, precise constraints, examples, structure, uncertainty handling.\n"
        "- 60-89: Solid; some aspects missing (e.g., examples/constraints).\n"
        "- 0-59: Weak; vague, lacks goal/context/format.\n"
        "Map the score to label: good (>=75), ok (45-74), bad (<45).\n"
        "Provide a concise improved_prompt that addresses top gaps."
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

