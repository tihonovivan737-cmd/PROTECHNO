"""Генератор PDF-отчётов по площадкам VK и Дзен.

Анализирует спаршенные данные, строит графики,
генерирует рекомендации через Ollama и сохраняет всё в PDF.
"""

import csv
import os
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # без GUI
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
)
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os as _os

import requests

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = os.getenv("OLLAMA_REPORT_MODEL", "qwen2.5:3b")

VK_CSV = "posts.csv"
DZEN_CSV = "dzen_posts.csv"


def _safe_int(value, default=0):
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _register_cyrillic_fonts():
    """Регистрирует шрифты Windows с поддержкой кириллицы."""
    fonts_dir = _os.path.join(_os.environ.get("WINDIR", "C:\\Windows"), "Fonts")
    fonts = {
        "Arial": "arial.ttf",
        "Arial-Bold": "arialbd.ttf",
        "Arial-Italic": "ariali.ttf",
        "Arial-BoldItalic": "arialbi.ttf",
    }
    registered = 0
    for name, filename in fonts.items():
        path = _os.path.join(fonts_dir, filename)
        if _os.path.exists(path):
            pdfmetrics.registerFont(TTFont(name, path))
            registered += 1
    return registered > 0


# ─────────────── Загрузка данных ───────────────

def load_vk_data(path: str = VK_CSV) -> list[dict]:
    if not Path(path).exists():
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return [row for row in csv.DictReader(f, delimiter=";")]


def load_dzen_data(path: str = DZEN_CSV) -> list[dict]:
    if not Path(path).exists():
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return [row for row in csv.DictReader(f, delimiter=";")]


# ─────────────── Аналитика ───────────────

def analyze_vk(posts: list[dict]) -> dict:
    if not posts:
        return {"error": "Нет данных по VK"}

    likes = [_safe_int(p.get("likes")) for p in posts]
    views = [_safe_int(p.get("views")) for p in posts]
    comments = [_safe_int(p.get("comments")) for p in posts]
    reposts = [_safe_int(p.get("reposts")) for p in posts]

    dates = []
    for p in posts:
        try:
            dates.append(datetime.strptime(p["date"], "%Y-%m-%d %H:%M:%S"))
        except (ValueError, KeyError):
            pass

    top_by_likes = sorted(posts, key=lambda x: _safe_int(x.get("likes")), reverse=True)[:5]
    top_by_views = sorted(posts, key=lambda x: _safe_int(x.get("views")), reverse=True)[:5]

    return {
        "platform": "VK",
        "total_posts": len(posts),
        "avg_likes": round(sum(likes) / len(likes), 1) if likes else 0,
        "avg_views": round(sum(views) / len(views), 1) if views else 0,
        "avg_comments": round(sum(comments) / len(comments), 1) if comments else 0,
        "max_likes": max(likes) if likes else 0,
        "max_views": max(views) if views else 0,
        "group_members": _safe_int(posts[0].get("group_members", 0)),
        "top_by_likes": top_by_likes,
        "top_by_views": top_by_views,
        "dates": sorted(dates),
        "likes_series": likes,
        "views_series": views,
    }


def analyze_dzen(posts: list[dict]) -> dict:
    if not posts:
        return {"error": "Нет данных по Дзену"}

    views = [_safe_int(p.get("views")) for p in posts]
    read_times = [_safe_int(p.get("time_to_read_sec")) for p in posts]

    top_by_views = sorted(posts, key=lambda x: _safe_int(x.get("views")), reverse=True)[:5]

    channel = posts[0].get("channel", "") if posts else ""

    return {
        "platform": "Дзен",
        "channel": channel,
        "total_posts": len(posts),
        "avg_views": round(sum(views) / len(views), 1) if views else 0,
        "max_views": max(views) if views else 0,
        "avg_read_time_sec": round(sum(read_times) / len(read_times), 1) if read_times else 0,
        "top_by_views": top_by_views,
    }


# ─────────────── Графики ───────────────

def create_vk_charts(stats: dict, charts_dir: str = "charts") -> list[str]:
    os.makedirs(charts_dir, exist_ok=True)
    charts = []

    if stats.get("dates"):
        plt.figure(figsize=(10, 4))
        plt.plot(stats["dates"], stats["views_series"], marker="o", linestyle="-", linewidth=2, markersize=4)
        plt.gcf().autofmt_xdate()
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
        plt.title("Просмотры по дате")
        plt.xlabel("Дата")
        plt.ylabel("Просмотры")
        plt.grid(True, alpha=0.3)
        path = os.path.join(charts_dir, "vk_views.png")
        plt.savefig(path, dpi=150, bbox_inches="tight")
        plt.close()
        charts.append(path)

        plt.figure(figsize=(10, 4))
        plt.plot(stats["dates"], stats["likes_series"], marker="s", linestyle="-", color="green", linewidth=2)
        plt.gcf().autofmt_xdate()
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
        plt.title("Лайки по дате")
        plt.xlabel("Дата")
        plt.ylabel("Лайки")
        plt.grid(True, alpha=0.3)
        path = os.path.join(charts_dir, "vk_likes.png")
        plt.savefig(path, dpi=150, bbox_inches="tight")
        plt.close()
        charts.append(path)

    return charts


def create_dzen_charts(stats: dict, charts_dir: str = "charts") -> list[str]:
    os.makedirs(charts_dir, exist_ok=True)
    charts = []

    if stats.get("top_by_views"):
        labels = [f"#{i+1}" for i in range(len(stats["top_by_views"]))]
        values = [_safe_int(p.get("views")) for p in stats["top_by_views"]]
        plt.figure(figsize=(8, 4))
        plt.bar(labels, values, color="orange")
        plt.title("Топ-5 постов по просмотрам")
        plt.xlabel("Пост")
        plt.ylabel("Просмотры")
        plt.grid(True, alpha=0.3, axis="y")
        path = os.path.join(charts_dir, "dzen_top.png")
        plt.savefig(path, dpi=150, bbox_inches="tight")
        plt.close()
        charts.append(path)

    return charts


# ─────────────── Рекомендации LLM ───────────────

def generate_recommendations(platform: str, stats: dict) -> str:
    """Запрашивает у Ollama рекомендации по контенту."""
    summary = (
        f"Площадка: {platform}\n"
        f"Всего постов: {stats.get('total_posts', 0)}\n"
        f"Средние просмотры: {stats.get('avg_views', 0)}\n"
        f"Средние лайки: {stats.get('avg_likes', 'Н/Д')}\n"
        f"Максимум просмотров: {stats.get('max_views', 0)}\n"
        f"Максимум лайков: {stats.get('max_likes', 'Н/Д')}\n"
    )

    top_posts = stats.get("top_by_likes") or stats.get("top_by_views", [])[:3]
    if top_posts:
        summary += "\nТоп-посты (текст):\n"
        for i, post in enumerate(top_posts[:3], 1):
            text = (post.get("text") or "")[:200]
            summary += f"{i}. {text}...\n"

    prompt = f"""Ты — SMM-аналитик. На основе статистики дай рекомендации по контенту.
Статистика:
{summary}

Дай 5 конкретных рекомендаций:
1. Какой контент работает лучше всего
2. В какое время лучше постить
3. Какие темы развивать
4. Как увеличить вовлечённость
5. Что изменить в стратегии

Отвечай кратко, по делу, без воды. Только рекомендации."""

    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.7, "num_predict": 600},
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["response"].strip()
    except Exception as e:
        return f"Ошибка при генерации рекомендаций: {e}"


# ─────────────── Генерация PDF ───────────────

def generate_pdf(platform: str, stats: dict, charts: list[str], recommendations: str,
                 output_path: str = "report.pdf") -> None:
    _register_cyrillic_fonts()

    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            topMargin=20*mm, bottomMargin=20*mm,
                            leftMargin=20*mm, rightMargin=20*mm)

    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("TitleCustom", parent=styles["Title"],
                                 fontSize=20, spaceAfter=10, alignment=TA_CENTER,
                                 fontName="Arial-Bold")
    h2_style = ParagraphStyle("H2Custom", parent=styles["Heading2"],
                              fontSize=14, spaceBefore=15, spaceAfter=8, textColor=colors.HexColor("#2C3E50"),
                              fontName="Arial-Bold")
    body_style = ParagraphStyle("BodyCustom", parent=styles["Normal"],
                                fontSize=11, leading=14, spaceAfter=6,
                                fontName="Arial")

    story.append(Paragraph(f"Аналитический отчёт: {platform}", title_style))
    story.append(Spacer(1, 5*mm))

    # Общая статистика
    story.append(Paragraph("Общая статистика", h2_style))

    table_data = [["Метрика", "Значение"]]
    metrics = [
        ("Всего постов", stats.get("total_posts", 0)),
        ("Средние просмотры", stats.get("avg_views", 0)),
        ("Максимум просмотров", stats.get("max_views", 0)),
    ]
    if "avg_likes" in stats:
        metrics.append(("Средние лайки", stats["avg_likes"]))
        metrics.append(("Максимум лайков", stats.get("max_likes", 0)))
    if "avg_comments" in stats:
        metrics.append(("Средние комментарии", stats.get("avg_comments", 0)))
    if "group_members" in stats:
        metrics.append(("Подписчиков", stats.get("group_members", 0)))

    for label, value in metrics:
        table_data.append([label, str(value)])

    table = Table(table_data, colWidths=[80*mm, 80*mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#34495E")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME", (0, 0), (-1, 0), "Arial-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 12),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#ECF0F1")),
        ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
        ("FONTNAME", (0, 1), (-1, -1), "Arial"),
        ("FONTSIZE", (0, 1), (-1, -1), 11),
        ("GRID", (0, 0), (-1, -1), 1, colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(table)
    story.append(Spacer(1, 5*mm))

    # Графики
    if charts:
        story.append(Paragraph("Графики", h2_style))
        for chart in charts:
            if Path(chart).exists():
                img = Image(chart, width=160*mm, height=60*mm)
                story.append(img)
                story.append(Spacer(1, 3*mm))

    # Рекомендации
    story.append(PageBreak())
    story.append(Paragraph("Рекомендации по контенту", h2_style))
    for line in recommendations.split("\n"):
        if line.strip():
            story.append(Paragraph(line.strip(), body_style))

    doc.build(story)
    print(f"Отчёт сохранён: {output_path}")


# ─────────────── Основной CLI ───────────────

def main():
    print("Генератор отчётов")
    print("1 — VK")
    print("2 — Дзен")
    choice = input("Выбери площадку [1/2]: ").strip()

    charts_dir = "charts"

    if choice == "1":
        platform = "VK"
        posts = load_vk_data()
        if not posts:
            print("Нет данных по VK. Запусти сначала parser.py.")
            return
        stats = analyze_vk(posts)
        charts = create_vk_charts(stats, charts_dir)
    elif choice == "2":
        platform = "Дзен"
        posts = load_dzen_data()
        if not posts:
            print("Нет данных по Дзену. Запусти сначала dzen_parser.py.")
            return
        stats = analyze_dzen(posts)
        charts = create_dzen_charts(stats, charts_dir)
    else:
        print("Неверный выбор.")
        return

    print(f"\nАнализирую {platform} ({stats.get('total_posts', 0)} постов)...")

    recommendations = generate_recommendations(platform, stats)

    output = f"report_{platform.lower()}.pdf"
    generate_pdf(platform, stats, charts, recommendations, output)


if __name__ == "__main__":
    main()
