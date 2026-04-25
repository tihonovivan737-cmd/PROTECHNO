"""Определение состояния сообщества (CRISIS / NORMAL / RISE) по ER постов.

ER считается как (likes + reposts + comments) / views для каждого поста.
Пороги CRISIS/RISE — это Q25/Q75 по rolling-средним (окно 5 постов) на всей истории.
Текущее состояние — по среднему ER последних 5 постов.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

WINDOW = 5
DEFAULT_POSTS_CSV = Path("posts.csv")


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
    state: str                 # "CRISIS" | "NORMAL" | "RISE"
    avg_er: float              # средний ER по последним WINDOW постам
    crisis_threshold: float    # Q25 rolling-средних
    rise_threshold: float      # Q75 rolling-средних
    sample_size: int           # сколько постов учтено для текущего окна


def _to_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def load_posts(path: Path = DEFAULT_POSTS_CSV) -> list[Post]:
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
    posts.sort(key=lambda p: p.date)  # от старых к новым
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


def assess(path: Path = DEFAULT_POSTS_CSV, window: int = WINDOW) -> ConditionResult:
    """Главная точка входа: читает CSV и возвращает текущее состояние."""
    posts = load_posts(path)
    if not posts:
        return ConditionResult("NORMAL", 0.0, 0.0, 0.0, 0)

    crisis_th, rise_th = compute_thresholds(posts, window=window)
    last = posts[-window:]
    avg_er = float(np.mean([p.er_post for p in last]))
    state = detect_state(avg_er, crisis_th, rise_th)
    return ConditionResult(state, avg_er, crisis_th, rise_th, len(last))


if __name__ == "__main__":
    res = assess()
    print(
        f"state={res.state} avg_er={res.avg_er:.4f} "
        f"crisis<{res.crisis_threshold:.4f} rise>{res.rise_threshold:.4f} "
        f"(by {res.sample_size} last posts)"
    )