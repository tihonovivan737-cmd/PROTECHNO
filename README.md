# Анализатор медиаокнтента для хакатона Протехно 2026

## Backend
Для запуска Backend пропишите в главной директории

uvicorn backend.app.main:app --reload

Примеры запросов/ответов
POST /api/vk/parse
Запрос:

{
  "url": "https://vk.com/svoedelomc",
  "max_posts": 3
}
Ответ:

{
  "domain": "svoedelomc",
  "count": 3,
  "posts": [
    {
      "id": 12345,
      "date": "2026-04-20T18:30:00",
      "text": "Сегодня в МЦ прошёл квиз...",
      "likes": 87,
      "reposts": 3,
      "comments": 5,
      "views": 1240
    }
  ]
}
Ошибка некорректной ссылки → 400, ошибка VK → 502.

POST /api/llm/generate
Запрос:

{ "query": "Кинопоказ под открытым небом на Татышеве в субботу" }
Ответ:

{
  "text": "В субботу собираемся на Татышеве...\n\n#мцсвоедело",
  "model": "qwen2.5:3b",
  "shots_used": 3
}
POST /api/vk/poster
Запрос:

{
  "message": "Тестовый пост из backend 🚀",
  "attachments": null,
  "from_group": true
}
Ответ (201):


{
  "post_id": 7842,
  "url": "https://vk.com/wall-238056064_7842"
}