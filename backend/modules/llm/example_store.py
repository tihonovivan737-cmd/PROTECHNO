import csv
import re
from abc import ABC, abstractmethod
from pathlib import Path


class BaseExampleStore(ABC):
    @abstractmethod
    def top_by_likes(self, n: int, min_len: int = 0, max_len: int = 10_000) -> list[dict]:
        raise NotImplementedError


class CSVExampleStore(BaseExampleStore):
    """Читает CSV с постами VK и возвращает топ по лайкам для few-shot-примеров."""

    _VK_LINK_RE = re.compile(r"\[(?:[^\]|]+)\|([^\]]+)\]")
    _MULTISPACE_RE = re.compile(r"[ \t]+")

    def __init__(self, path: Path):
        self.rows = self._load(path)

    @classmethod
    def _load(cls, path: Path) -> list[dict]:
        if not path.exists():
            raise FileNotFoundError(f"CSV не найден: {path}")
        with path.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            rows: list[dict] = []
            for r in reader:
                text = cls._clean_text(r.get("text", ""))
                if not text:
                    continue
                rows.append({
                    "id": r.get("id", ""),
                    "date": r.get("date", ""),
                    "text": text,
                    "likes": cls._to_int(r.get("likes")),
                    "views": cls._to_int(r.get("views")),
                })
            return rows

    @classmethod
    def _clean_text(cls, text: str) -> str:
        text = cls._VK_LINK_RE.sub(r"\1", text)
        text = text.replace("\u00a0", " ")
        text = cls._MULTISPACE_RE.sub(" ", text)
        return text.strip()

    @staticmethod
    def _to_int(value) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def top_by_likes(self, n: int, min_len: int = 0, max_len: int = 10_000) -> list[dict]:
        filtered = [r for r in self.rows if min_len <= len(r["text"]) <= max_len]
        return sorted(filtered, key=lambda r: r["likes"], reverse=True)[:n]
