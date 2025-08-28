import re
from typing import List, Tuple, Optional

from .models import EvaluationResponse, Subscore, Suggestion


imperatives = [
    "write", "generate", "summarize", "translate", "explain",
    "classify", "extract", "draft", "improve", "edit", "rewrite",
]


def _has_role(text: str) -> Tuple[int, str]:
    if re.search(r"\b(you are|act as|role:|persona:)\b", text, re.I):
        return 5, "Has explicit role/persona"
    return 2, "Add a role/persona (e.g., 'You are a data analyst')."


def _has_goal(text: str, goal: Optional[str]) -> Tuple[int, str]:
    if goal and len(goal.strip()) >= 8:
        return 5, "Explicit goal provided via UI"
    if any(re.search(fr"\b{w}\b", text, re.I) for w in imperatives):
        return 4, "Contains an objective verb"
    return 1, "Clarify the objective (what to produce)."


def _has_context(text: str) -> Tuple[int, str]:
    if re.search(r"\b(context:|given|here is|background:)\b", text, re.I):
        return 5, "Includes context/background"
    if len(text.split()) > 60:
        return 3, "Some context implied by length"
    return 2, "Provide key context or constraints."


def _has_constraints(text: str) -> Tuple[int, str]:
    hits = 0
    hits += 1 if re.search(r"\b(in \d+ (words|sentences|bullets|lines))\b", text, re.I) else 0
    hits += 1 if re.search(r"\b(exactly|no more than|at most|at least|must)\b", text, re.I) else 0
    hits += 1 if re.search(r"\b(format|schema|json|table|markdown)\b", text, re.I) else 0
    if hits >= 2:
        return 5, "Clear constraints and format"
    if hits == 1:
        return 3, "Some constraints present"
    return 2, "Specify output format/length/structure."


def _has_examples(text: str) -> Tuple[int, str]:
    if re.search(r"\b(example|examples|input:|output:|q:|a:)\b", text, re.I):
        return 4, "Contains examples or IO pairs"
    return 2, "Add a small example (few-shot) if helpful."


def _has_evaluation(text: str) -> Tuple[int, str]:
    if re.search(r"\b(rubric|criteria|accept|grading|score)\b", text, re.I):
        return 4, "Defines evaluation criteria"
    if re.search(r"\b(if (unsure|unknown)|cannot be determined|say 'i (can|cannot)')\b", text, re.I):
        return 3, "Has uncertainty handling"
    return 1, "Add acceptance criteria or uncertainty handling."


def _has_safety_grounding(text: str) -> Tuple[int, str]:
    if re.search(r"\b(cite|source|reference|link)\b", text, re.I):
        return 3, "Asks for sources/citations"
    if re.search(r"\b(ask clarifying questions|clarifying question|if missing)\b", text, re.I):
        return 4, "Encourages clarification when needed"
    return 2, "Optionally ask for citations or clarifying questions."


def _has_structure(text: str) -> Tuple[int, str]:
    if re.search(r"\b(steps|bullets|sections|headings)\b", text, re.I) or "\n- " in text:
        return 4, "Structured output requested"
    return 2, "Request structured output (bullets/sections)."


def _label_from_score(score: int) -> str:
    if score >= 75:
        return "good"
    if score >= 45:
        return "ok"
    return "bad"


def score_prompt(prompt: str, goal: Optional[str] = None) -> EvaluationResponse:
    text = prompt.strip()
    # Compute subscores
    subs: List[Tuple[str, int, str]] = []
    for name, fn in [
        ("Role", _has_role),
        ("Goal", lambda t: _has_goal(t, goal)),
        ("Context", _has_context),
        ("Constraints", _has_constraints),
        ("Examples", _has_examples),
        ("Evaluation", _has_evaluation),
        ("Structure", _has_structure),
        ("Safety", _has_safety_grounding),
    ]:
        s, c = fn(text)
        subs.append((name, s, c))

    # Normalize to 100
    max_points = 5 * len(subs)
    raw = sum(s for _, s, _ in subs)
    score = int(round(100 * raw / max_points))
    label = _label_from_score(score)

    feedback: List[str] = []
    for name, s, c in subs:
        if s <= 3:
            feedback.append(f"{name}: {c}")

    suggestions: List[Suggestion] = []
    if any(n == "Constraints" and s <= 3 for n, s, _ in subs):
        suggestions.append(Suggestion(
            title="Specify format",
            text="Return JSON with keys: 'answer', 'assumptions'.",
        ))
    if any(n == "Examples" and s <= 3 for n, s, _ in subs):
        suggestions.append(Suggestion(
            title="Add a small example",
            text="Include one Input/Output pair to set expectations.",
        ))
    if any(n == "Evaluation" and s <= 3 for n, s, _ in subs):
        suggestions.append(Suggestion(
            title="Define success",
            text="State acceptance criteria or what makes a good answer.",
        ))
    if any(n == "Safety" and s <= 3 for n, s, _ in subs):
        suggestions.append(Suggestion(
            title="Handle uncertainty",
            text="If info is missing, ask clarifying questions rather than guessing.",
        ))

    improved = build_improved_prompt(prompt, goal, subs)

    subscores = [Subscore(name=n, score=s, comment=c) for n, s, c in subs]
    summary = (
        "Well-structured prompt with clear objective and constraints."
        if label == "good" else
        "Decent prompt; add context/constraints/examples to improve."
        if label == "ok" else
        "Underspecified prompt; clarify goal, context, and format."
    )

    return EvaluationResponse(
        label=label,
        score=score,
        summary=summary,
        subscores=subscores,
        feedback=feedback,
        suggestions=suggestions,
        improved_prompt=improved,
    )


def build_improved_prompt(prompt: str, goal: Optional[str], subs: List[Tuple[str, int, str]]) -> str:
    # Build a simple template-based improved prompt
    has_role = next((s for n, s, _ in subs if n == "Role"), 0) >= 4
    has_constraints = next((s for n, s, _ in subs if n == "Constraints"), 0) >= 4
    has_structure = next((s for n, s, _ in subs if n == "Structure"), 0) >= 4

    role_line = "You are a helpful assistant." if not has_role else None
    goal_text = goal or "State the objective here."

    parts: List[str] = []
    if role_line:
        parts.append(role_line)
    parts.append(f"Goal: {goal_text}")
    parts.append("Context: Add any relevant background or inputs here.")
    if not has_constraints:
        parts.append("Constraints: Return a concise answer in under 120 words.")
        parts.append("Format: JSON with keys 'answer' and 'assumptions'.")
    if not has_structure:
        parts.append("Structure: Use bullet points for clarity where applicable.")
    parts.append("If information is missing, ask up to 2 clarifying questions before answering.")
    parts.append("Examples:\nInput: <short example>\nOutput: <desired style>")

    return "\n\n".join(parts)

