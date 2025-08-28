import re
from typing import List, Tuple, Optional

from .models import EvaluationResponse, Subscore, Suggestion


question_words = ["who", "what", "when", "where", "why", "how", "which"]


def _clarity(text: str) -> Tuple[int, str]:
    has_qmark = "?" in text
    has_qword = any(re.search(fr"\b{w}\b", text, re.I) for w in question_words)
    words = len(text.split())
    if has_qmark and has_qword and words >= 6:
        return 5, "Clear, direct question"
    if has_qmark or has_qword:
        return 4, "Question is somewhat clear"
    if words < 6:
        return 2, "Too short/vague to understand"
    return 3, "Make it a direct question with a clear ask."


def _specificity(text: str, goal: Optional[str]) -> Tuple[int, str]:
    hits = 0
    if re.search(r"\b(\d+|top \d+|at least|no more than)\b", text, re.I):
        hits += 1
    if re.search(r"\b(for|about|regarding|focused on)\b", text, re.I):
        hits += 1
    if goal and len(goal.strip()) >= 8:
        hits += 1
    if hits >= 3:
        return 5, "Specific objective and constraints"
    if hits == 2:
        return 4, "Reasonably specific"
    if hits == 1:
        return 3, "Add more specifics (topic/audience/count)."
    return 2, "Too general—narrow the scope."


def _context(text: str) -> Tuple[int, str]:
    if re.search(r"\b(context:|given|below|attached|based on|here is)\b", text, re.I):
        return 5, "Provides relevant context"
    if len(text.split()) > 60:
        return 3, "Some context implied by length"
    return 2, "Provide key background or inputs."


def _constraints_and_format(text: str) -> Tuple[int, str]:
    hits = 0
    if re.search(r"\b(in \d+ (words|sentences|bullets|lines))\b", text, re.I):
        hits += 1
    if re.search(r"\b(format|schema|json|table|markdown|bullets?)\b", text, re.I):
        hits += 1
    if re.search(r"\b(tone|style|audience|level)\b", text, re.I):
        hits += 1
    if hits >= 2:
        return 5, "Clear constraints and expected format"
    if hits == 1:
        return 3, "Some constraints present"
    return 2, "Specify length, audience, or format."


def _scope_feasibility(text: str) -> Tuple[int, str]:
    if re.search(r"\b(everything|anything|all about|complete guide)\b", text, re.I):
        return 2, "Scope is too broad—narrow it."
    if len(text.split()) < 6:
        return 2, "Too short to determine scope"
    return 4, "Scope seems reasonable"


def _neutrality(text: str) -> Tuple[int, str]:
    if re.search(r"why is .* better than|prove that|obviously|clearly", text, re.I):
        return 2, "Question appears leading or biased. Consider neutral phrasing."
    return 4, "Neutral phrasing"


def _outcome_oriented(text: str) -> Tuple[int, str]:
    if re.search(r"\b(so that|goal|use this to|I need to)\b", text, re.I):
        return 4, "Mentions desired outcome/use"
    return 3, "Optionally state intended outcome to guide answers."


def _clarification_handling(text: str) -> Tuple[int, str]:
    if re.search(r"\b(ask (a )?clarifying question|if .* missing|if .* unclear|if unsure)\b", text, re.I):
        return 5, "Invites clarification for ambiguities"
    return 3, "Encourage clarifying questions when info is missing."


def _label_from_score(score: int) -> str:
    if score >= 75:
        return "good"
    if score >= 45:
        return "ok"
    return "bad"


def score_prompt(prompt: str, goal: Optional[str] = None) -> EvaluationResponse:
    text = prompt.strip()
    # Compute subscores focused on question quality
    subs: List[Tuple[str, int, str]] = []
    for name, fn in [
        ("Clarity", _clarity),
        ("Specificity", lambda t: _specificity(t, goal)),
        ("Context", _context),
        ("Constraints & Format", _constraints_and_format),
        ("Scope & Feasibility", _scope_feasibility),
        ("Neutrality", _neutrality),
        ("Outcome Orientation", _outcome_oriented),
        ("Clarification", _clarification_handling),
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
    if any(n == "Clarity" and s <= 3 for n, s, _ in subs):
        suggestions.append(Suggestion(
            title="Ask a direct question",
            text="Use a single, specific question (e.g., 'How can I ...?').",
        ))
    if any(n == "Specificity" and s <= 3 for n, s, _ in subs):
        suggestions.append(Suggestion(
            title="Narrow the focus",
            text="Add audience, topic, and numbers (e.g., 'top 3', 'in 200 words').",
        ))
    if any(n == "Constraints & Format" and s <= 3 for n, s, _ in subs):
        suggestions.append(Suggestion(
            title="Set expectations",
            text="Request a format (bullets/table/JSON) and length/tone.",
        ))
    if any(n == "Scope & Feasibility" and s <= 3 for n, s, _ in subs):
        suggestions.append(Suggestion(
            title="Right-size the scope",
            text="Avoid 'everything/anything'; ask for the most relevant parts.",
        ))
    if any(n == "Neutrality" and s <= 3 for n, s, _ in subs):
        suggestions.append(Suggestion(
            title="Use neutral phrasing",
            text="Prefer 'Compare X and Y' over 'Why is X better?'.",
        ))
    if any(n == "Clarification" and s <= 3 for n, s, _ in subs):
        suggestions.append(Suggestion(
            title="Invite questions",
            text="Allow 1–2 clarifying questions if information is missing.",
        ))

    improved = build_improved_prompt(prompt, goal, subs)

    subscores = [Subscore(name=n, score=s, comment=c) for n, s, c in subs]
    summary = (
        "Strong question—clear, specific, and easy to answer."
        if label == "good" else
        "Decent question—add context, specifics, or format to improve."
        if label == "ok" else
        "Vague question—clarify ask, scope, context, and format."
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
    # Build an improved question that is clear, specific, and answerable
    needs_format = next((s for n, s, _ in subs if n == "Constraints & Format"), 0) <= 3
    needs_specificity = next((s for n, s, _ in subs if n == "Specificity"), 0) <= 3
    needs_context = next((s for n, s, _ in subs if n == "Context"), 0) <= 3

    g = goal or "State your purpose (e.g., for executives)."
    parts: List[str] = []
    # Direct question stem
    parts.append(f"Question: How can I {('best ' if not needs_specificity else '')}achieve this goal?")
    if needs_context:
        parts.append("Context: Briefly include the most relevant background or inputs.")
    if needs_specificity:
        parts.append("Specifics: Limit to top 3 points and focus on what's actionable.")
    if needs_format:
        parts.append("Format: Return 5 bullet points and a short summary (<=120 words).")
    parts.append("If information is missing, ask up to 2 clarifying questions before answering.")
    parts.append(f"Goal: {g}")
    return "\n\n".join(parts)
