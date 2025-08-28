"""Helpers to load curated BAD/OK/GOOD examples from JSON."""

import json
import random
from pathlib import Path
from typing import List

from .models import ExampleItem


DATA_PATH = Path(__file__).parent / "data" / "examples.json"


def load_examples() -> List[ExampleItem]:
    """Load the examples JSON file and parse into `ExampleItem` objects.

    Raises `json.JSONDecodeError` if the file is malformed.
    """
    with DATA_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return [ExampleItem(**row) for row in data]


def get_random_example(examples: List[ExampleItem]) -> ExampleItem:
    """Pick a random example from a preloaded list."""
    return random.choice(examples) if examples else ExampleItem(
        id="empty",
        bad="",
        ok="",
        good="",
        explanation="",
    )
