import re
from typing import List, Tuple, Optional

from .models import EvaluationResponse, Subscore, Suggestion


# Simpler, user-friendly rubric: 4 attributes scored 0/1/2
question_words = ["who", "what", "when", "where", "why", "how", "which"]


def _clarity(text: str) -> Tuple[int, str]:
    has_qmark = "?" in text
    has_qword = any(re.search(fr"\b{w}\b", text, re.I) for w in question_words)
    words = len(text.split())
    if has_qmark and has_qword and words >= 6:
        return 2, "Single, direct question"
    if has_qmark or has_qword:
        return 1, "Somewhat direct"
    return 0, "Ask one clear question."


def _specificity(text: str) -> Tuple[int, str]:
    hits = 0
    if re.search(r"\b(\d+|top \d+|in \d+ (words|bullets))\b", text, re.I):
        hits += 1
    if re.search(r"\b(for|about|regarding|focused on|for (beginners|executives|students))\b", text, re.I):
        hits += 1
    if re.search(r"\b(week|month|30 days|deadline)\b", text, re.I):
        hits += 1
    if hits >= 2:
        return 2, "Specific scope"
    if hits == 1:
        return 1, "Some specifics"
    return 0, "Add topic/audience/numbers."


def _context(text: str) -> Tuple[int, str]:
    # Score context based on content signals, not explicit markers
    has_url = bool(re.search(r"https?://\S+", text))
    has_code_like = ("```" in text) or bool(re.search(r"`[^`]{10,}`", text))
    has_structured = bool(re.search(r"\{[^\}]{10,}\}|\[[^\]]{10,}\]", text))
    has_list = bool(re.search(r"(^\s*[-*]\s+|^\s*\d+\.\s+)", text, re.M))
    digits = len(re.findall(r"\d", text))
    has_numbers = digits >= 3
    word_count = len(text.split())

    strong_signals = sum([has_url, has_code_like, has_structured, has_list, has_numbers])
    if strong_signals >= 2:
        return 2, "Includes usable context"
    if strong_signals >= 1 or word_count > 40:
        return 1, "Some context present"
    return 0, "Add essential background or inputs."


def _format(text: str) -> Tuple[int, str]:
    hits = 0
    if re.search(r"\b(in \d+ (words|sentences|bullets|lines))\b", text, re.I):
        hits += 1
    if re.search(r"\b(json|table|markdown|bullets?|schema|format)\b", text, re.I):
        hits += 1
    if re.search(r"\b(tone|style|level)\b", text, re.I):
        hits += 1
    if hits >= 2:
        return 2, "Clear format/length"
    if hits == 1:
        return 1, "Some formatting"
    return 0, "Set length and format."


def _label_from_score(score: int) -> str:
    if score >= 75:
        return "good"
    if score >= 45:
        return "ok"
    return "bad"


def score_prompt(prompt: str, goal: Optional[str] = None) -> EvaluationResponse:
    text = prompt.strip()
    core: List[Tuple[str, int, str]] = [
        ("Clarity",) + _clarity(text),
        ("Specificity",) + _specificity(text),
        ("Context",) + _context(text),
        ("Constraints & Format",) + _format(text),
    ]

    # 0–8 mapped to 0–100
    raw = sum(s for _, s, _ in core)
    score = int(round(raw * 12.5))
    label = _label_from_score(score)

    # Short, actionable feedback (max 3 items)
    weakest = sorted(core, key=lambda t: t[1])[:3]
    feedback = [f"{n}: {c}" for n, s, c in weakest if s < 2]

    suggestions: List[Suggestion] = []
    for n, s, _ in core:
        if n == "Clarity" and s < 2:
            suggestions.append(Suggestion(title="Ask one question", text="Start with 'How/What/Why ...?'"))
        if n == "Specificity" and s < 2:
            suggestions.append(Suggestion(title="Be specific", text="Add audience/topic and numbers (e.g., 'top 3')."))
        if n == "Context" and s < 2:
            suggestions.append(Suggestion(title="Add context", text="Include the key background/input needed."))
        if n == "Constraints & Format" and s < 2:
            suggestions.append(Suggestion(title="Set format", text="Ask for bullets/table/JSON and a word limit."))

    improved = build_improved_prompt(prompt, goal, core)

    subscores = [Subscore(name=n, score=s, comment=c) for n, s, c in core]
    summary = (
        "Strong question—clear, specific, and easy to answer."
        if label == "good" else
        "Decent question—tighten specifics, context, or format."
        if label == "ok" else
        "Vague question—clarify ask, add context, set format."
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
    # Produce a single, rewritten question/instruction (no meta text)
    needs_format = next((s for n, s, _ in subs if n == "Constraints & Format"), 0) <= 1
    needs_specificity = next((s for n, s, _ in subs if n == "Specificity"), 0) <= 1
    needs_context = next((s for n, s, _ in subs if n == "Context"), 0) <= 1

    base = " ".join((prompt or "").strip().split())
    if not base:
        base = "Explain the topic clearly."

    tail: List[str] = []
    if needs_specificity:
        tail.append("Focus on the top 3 most important points.")
    if needs_format:
        tail.append("Return exactly 5 bullet points and a short summary (<=120 words).")
    if needs_context:
        # Encourage including context implicitly by asking for relevance
        tail.append("Prioritize details that are most relevant to the goal.")

    if tail:
        sep = " " if base.endswith(('.', '?')) else ". "
        base = base + sep + " ".join(tail)
    return base
