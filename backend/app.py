"""FastAPI application for the Prompt Engineering Trainer.

Exposes endpoints to:
- Evaluate a question/prompt (with optional LLM via Ollama)
- Fetch quiz items and submit answers
- Serve curated examples of BAD/OK/GOOD prompts with explanations

Interactive API docs (Swagger UI): /docs
ReDoc: /redoc
"""

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path

from .scoring import score_prompt
from .models import EvaluationResponse, Suggestion, QuizItem, QuizSubmission, QuizResult, ExampleItem
from .quiz import get_quiz_items
from .config import load_config
from .llm_eval import evaluate_with_ollama
from .examples import load_examples


tags_metadata = [
    {"name": "Health", "description": "Service status endpoint."},
    {"name": "Evaluation", "description": "Evaluate questions/prompts and get feedback and an improved rewrite."},
    {"name": "Quiz", "description": "Practice identifying BAD/OK/GOOD prompts."},
    {"name": "Examples", "description": "Curated prompt examples with explanations."},
]

app = FastAPI(
    title="Prompt Engineering Trainer",
    version="0.2.2",
    description=(
        "Train better LLM questions: evaluate clarity, specificity, context, and format; "
        "practice with a quiz; browse examples that improve from BAD → OK → GOOD."
    ),
    contact={
        "name": "Prompt Trainer",
        "url": "https://example.com",
        "email": "team@example.com",
    },
    license_info={"name": "MIT"},
    openapi_tags=tags_metadata,
)
CONFIG = load_config()

# Allow local dev frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Avoid noisy 404s for browsers requesting /favicon.ico
@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


class EvaluateRequest(BaseModel):
    """Request body for /api/evaluate.

    - prompt: The user's question/prompt to evaluate.
    - goal: Optional intended use; currently unused by the UI but supported by the API.
    """

    prompt: str
    goal: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "prompt": "Explain the differences between SQL and NoSQL in 5 bullets for a beginner.",
                "goal": None,
            }
        }
    }


@app.get("/health", tags=["Health"], summary="Service health", description="Returns a simple OK status.")
def health():
    return {"status": "ok"}


@app.post(
    "/api/evaluate",
    response_model=EvaluationResponse,
    tags=["Evaluation"],
    summary="Evaluate a question/prompt",
    description=(
        "Scores question quality on four attributes (0–2 each), returns an overall score and label, "
        "actionable feedback, and an improved rewritten prompt. Uses Ollama if enabled; "
        "falls back to a heuristic evaluator otherwise."
    ),
)
async def evaluate_prompt(body: EvaluateRequest):
    # Basic validation to prevent empty or oversized prompts
    if not body.prompt or not body.prompt.strip():
        raise HTTPException(status_code=422, detail="Prompt cannot be empty. Please type your question.")
    if len(body.prompt) > 4000:
        raise HTTPException(status_code=422, detail="Prompt is too long (over 4000 characters). Please shorten it.")

    # Try LLM-based evaluation if enabled; fall back to heuristic
    llm_result = await evaluate_with_ollama(body.prompt, body.goal, CONFIG)
    if llm_result is not None:
        return llm_result
    return score_prompt(body.prompt, body.goal)


@app.get(
    "/api/quiz",
    response_model=List[QuizItem],
    tags=["Quiz"],
    summary="Get quiz items",
    description="Returns up to `limit` quiz items, sampled to ensure label balance where possible.",
)
def list_quiz_items(limit: int = 10):
    items = get_quiz_items(limit)
    return items


@app.post(
    "/api/quiz/submit",
    response_model=QuizResult,
    tags=["Quiz"],
    summary="Submit quiz answers",
    description="Grades provided labels against the expected ones and returns a score and details.",
)
def submit_quiz(submission: QuizSubmission):
    # Grade answers
    correct = 0
    details = []
    items_by_id = {item.id: item for item in get_quiz_items(limit=1000)}
    for answer in submission.answers:
        item = items_by_id.get(answer.item_id)
        if not item:
            details.append({
                "item_id": answer.item_id,
                "correct": False,
                "expected": None,
                "explanation": "Unknown item",
            })
            continue
        is_correct = (answer.label.lower() == item.label.lower())
        correct += 1 if is_correct else 0
        details.append({
            "item_id": item.id,
            "correct": is_correct,
            "expected": item.label,
            "explanation": item.rationale,
        })

    total = len(submission.answers)
    score = round(100 * correct / total, 1) if total else 0.0
    return QuizResult(score=score, total=total, correct=correct, details=details)


@app.get(
    "/api/examples",
    response_model=List[ExampleItem],
    tags=["Examples"],
    summary="List curated examples",
    description="Returns BAD/OK/GOOD prompt examples with per-level explanations and detailed notes.",
)
def list_examples():
    # Load from disk each request to reflect latest examples without restart
    return load_examples()

# Optionally serve the frontend statically from / when present — added after API
# routes so that /api/* takes priority over the static mount.
ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
