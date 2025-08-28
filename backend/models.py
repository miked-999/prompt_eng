from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Any

Label = Literal["good", "ok", "bad"]


class Subscore(BaseModel):
    name: str
    score: int = Field(ge=0, le=5)
    comment: str


class Suggestion(BaseModel):
    title: str
    text: str


class EvaluationResponse(BaseModel):
    label: Label
    score: int = Field(ge=0, le=100)
    summary: str
    subscores: List[Subscore]
    feedback: List[str]
    suggestions: List[Suggestion]
    improved_prompt: Optional[str] = None


class QuizItem(BaseModel):
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

