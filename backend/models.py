"""Pydantic models used by the API."""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Any

Label = Literal["good", "ok", "bad"]


class Subscore(BaseModel):
    """Named subscore for a question attribute.

    - name: Attribute name (e.g., Clarity, Specificity, Context, Constraints & Format)
    - score: 0–2 (heuristic) or up to 5 if returned by an LLM
    - comment: Short comment for the attribute
    """

    name: str
    score: int = Field(ge=0, le=5, description="Attribute score (0–2 for heuristic; up to 5 for LLM).")
    comment: str


class Suggestion(BaseModel):
    """Actionable suggestion with a short title and body."""

    title: str
    text: str


class EvaluationResponse(BaseModel):
    """Response for question evaluation."""

    label: Label
    score: int = Field(ge=0, le=100, description="Overall score from 0 to 100.")
    summary: str
    subscores: List[Subscore]
    feedback: List[str]
    suggestions: List[Suggestion]
    improved_prompt: Optional[str] = None


class QuizItem(BaseModel):
    """A quiz item with an expected label and rationale."""

    id: str
    prompt: str
    label: Label
    rationale: str


class QuizAnswer(BaseModel):
    item_id: str
    label: Label


class QuizSubmission(BaseModel):
    answers: List[QuizAnswer]


class QuizResult(BaseModel):
    score: float
    total: int
    correct: int
    details: List[Any]


class ExampleItem(BaseModel):
    """Curated BAD/OK/GOOD example with explanations."""

    id: str
    bad: str
    ok: str
    good: str
    # Per-level explanations shown on the right side
    bad_explanation: str | None = None
    ok_explanation: str | None = None
    good_explanation: str | None = None
    # Detailed, full-width explanation after GOOD
    details: str | None = None
