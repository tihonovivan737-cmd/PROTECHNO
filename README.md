# PROTECHNO Media Analyzer

Веб-приложение для анализа медиаконтента и генерации материалов в рамках проекта PROTECHNO.

Стек:
- Backend: FastAPI, SQLAlchemy, PostgreSQL
- Frontend: Vite + JavaScript
- Интеграции: VK, Dzen, Google Sheets, LLM

## Возможности

- Парсинг постов из VK и Dzen
- Аналитика и проверка состояния контента
- Генерация текста через LLM
- Формирование отчетов
- Профили организаций и маршрутизация сценариев

## Структура проекта

- `backend/` - API, бизнес-логика, БД-модели
- `frontend/` - клиентская часть (Vite)
- `alembic/` - миграции БД
- `start-dev.bat` - быстрый запуск dev-режима
- `start-prod.bat` - сборка фронтенда + запуск backend в prod-режиме

## Быстрый старт

### 1) Подготовка окружения

Требования:
- Python 3.10+
- Node.js 20+
- PostgreSQL

Установите зависимости backend:

```bash
pip install -r requirements.txt
```

Установите зависимости frontend:

```bash
cd frontend
npm install
```

### 2) Настройка `.env`

Создайте или заполните `.env` в корне проекта.
Минимально нужны параметры подключения к БД и ключи интеграций (VK/LLM).

### 3) Запуск в dev

Вариант 1 (рекомендуется для Windows):

```bat
start-dev.bat
```

Вариант 2 (вручную):

```bash
# терминал 1
python -m backend.app.main

# терминал 2
cd frontend
npm run dev
```

По умолчанию:
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`

### 4) Запуск в prod

```bat
start-prod.bat
```

Скрипт собирает frontend и поднимает единый сервер FastAPI, который отдает и API, и собранный фронтенд.

## Ключевые эндпоинты

- `GET /health/db` - проверка доступности БД
- `POST /api/vk/parse` - парсинг постов VK
- `POST /api/vk/poster` - публикация поста в VK
- `POST /api/llm/generate` - генерация текста LLM

## Примечания

- CORS настроен для localhost, локальной сети и временных tunnel-доменов (`trycloudflare.com`, `ngrok`).
- Для LAN-доступа откройте порты в Windows Firewall при необходимости.

## Лицензия

Внутренний проект команды PROTECHNO.
