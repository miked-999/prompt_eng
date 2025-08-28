import json
import random
from pathlib import Path
from typing import List

from .models import QuizItem


DATA_PATH = Path(__file__).parent / "data" / "quiz.json"


def _load_all() -> List[QuizItem]:
    with DATA_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return [QuizItem(**row) for row in data]


def get_quiz_items(limit: int = 10) -> List[QuizItem]:
    items = _load_all()
    if not items:
        return []

    k = min(limit, len(items))

    # Ensure at least 2 of each label (bad/ok/good) when possible
    buckets = {"bad": [], "ok": [], "good": []}
    for it in items:
        if it.label in buckets:
            buckets[it.label].append(it)

    chosen: List[QuizItem] = []
    needed_per_label = 2 if k >= 6 else 1
    for label, bucket in buckets.items():
        take = min(needed_per_label, len(bucket))
        if take > 0:
            chosen.extend(random.sample(bucket, take))

    # Fill remaining slots randomly from the rest
    remaining = [it for it in items if it not in chosen]
    remaining_slots = k - len(chosen)
    if remaining_slots > 0 and remaining:
        chosen.extend(random.sample(remaining, min(remaining_slots, len(remaining))))

    random.shuffle(chosen)
    return chosen[:k]
