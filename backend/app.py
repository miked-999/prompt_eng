from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from .scoring import score_prompt
from .models import EvaluationResponse, Suggestion, QuizItem, QuizSubmission, QuizResult
from .quiz import get_quiz_items
from .config import load_config
from .llm_eval import evaluate_with_ollama


app = FastAPI(title="Prompt Engineering Trainer", version="0.2.0")
CONFIG = load_config()

# Allow local dev frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class EvaluateRequest(BaseModel):
    prompt: str
    goal: Optional[str] = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/evaluate", response_model=EvaluationResponse)
async def evaluate_prompt(body: EvaluateRequest):
    # Try LLM-based evaluation if enabled; fall back to heuristic
    llm_result = await evaluate_with_ollama(body.prompt, body.goal, CONFIG)
    if llm_result is not None:
        return llm_result
    return score_prompt(body.prompt, body.goal)


@app.get("/api/quiz", response_model=List[QuizItem])
def list_quiz_items(limit: int = 10):
    items = get_quiz_items(limit)
    return items


@app.post("/api/quiz/submit", response_model=QuizResult)
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
