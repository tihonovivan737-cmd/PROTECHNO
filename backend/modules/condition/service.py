"""Определение состояния сообщества (CRISIS / NORMAL / RISE) по ER постов.

ER считается как (likes + reposts + comments) / views для каждого поста.
Пороги CRISIS/RISE — Q25/Q75 по rolling-средним (окно 5 постов).
Текущее состояние — по среднему ER последних N постов.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

WINDOW = 5


@dataclass
class Post:
    date: str
    likes: int
    reposts: int
    comments: int
    views: int

    @property
    def er_post(self) -> float:
        if self.views <= 0:
            return 0.0
        return (self.likes + self.reposts + self.comments) / self.views


@dataclass
class ConditionResult:
    state: str
    avg_er: float
    crisis_threshold: float
    rise_threshold: float
    sample_size: int


def _to_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def load_posts(path: Path) -> list[Post]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        posts = [
            Post(
                date=row.get("date", ""),
                likes=_to_int(row.get("likes")),
                reposts=_to_int(row.get("reposts")),
                comments=_to_int(row.get("comments")),
                views=_to_int(row.get("views")),
            )
            for row in reader
        ]
    posts.sort(key=lambda p: p.date)
    return posts


def compute_thresholds(posts: list[Post], window: int = WINDOW) -> tuple[float, float]:
    """Считает Q25/Q75 по rolling-средним ER с окном `window`."""
    er = [p.er_post for p in posts]
    if len(er) < window:
        return 0.0, 0.0

    rolling = [float(np.mean(er[i - window + 1 : i + 1])) for i in range(window - 1, len(er))]
    if not rolling:
        return 0.0, 0.0

    return float(np.percentile(rolling, 25)), float(np.percentile(rolling, 75))


def detect_state(avg_er: float, crisis_threshold: float, rise_threshold: float) -> str:
    if avg_er < crisis_threshold:
        return "CRISIS"
    if avg_er > rise_threshold:
        return "RISE"
    return "NORMAL"


def assess(path: Path, window: int = WINDOW) -> ConditionResult:
    """Читает CSV и возвращает текущее состояние сообщества."""
    posts = load_posts(path)
    if not posts:
        return ConditionResult("NORMAL", 0.0, 0.0, 0.0, 0)

    crisis_th, rise_th = compute_thresholds(posts, window=window)
    last = posts[-window:]
    avg_er = float(np.mean([p.er_post for p in last]))
    state = detect_state(avg_er, crisis_th, rise_th)
    return ConditionResult(state, avg_er, crisis_th, rise_th, len(last))
