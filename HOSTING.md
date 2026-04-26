# Локальный хостинг (доступ с любого устройства)

Два режима: **dev** (Vite + uvicorn по разным портам, hot-reload) и **prod**
(один порт, FastAPI отдаёт собранный фронт). Везде HTTP.

## 0. Узнай свой LAN-IP

Windows:
```powershell
ipconfig | Select-String IPv4
```

Из папки фронта (быстрый аналог):
```bash
npm run host:ip
```

Дальше под `<LAN-IP>` подразумевается, например, `192.168.1.42`.

## 1. Dev-режим (с hot-reload)

Бэк (порт `8000`, слушает все интерфейсы):
```bash
# из C:\Users\Вадим\protechno-media-analyzer
python -m backend.app.main
# либо классически:
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Фронт (порт `5173`, тоже на 0.0.0.0):
```bash
# из D:\DS\Pro-Techno
npm run dev
# (vite.config.ts уже стоит host: true, отдельный dev:lan не нужен)
```

С телефона: `http://<LAN-IP>:5173/` — всё, что начинается с `/api/`,
Vite сам проксирует на `http://127.0.0.1:8000`.

Если бэк крутится на другой машине — задай Vite адрес бэка:
```bash
# Windows powershell
$env:VITE_BACKEND_TARGET = "http://192.168.1.50:8000"; npm run dev
```

## 2. Prod-режим (один порт, без Node)

Соберём фронт:
```bash
# из D:\DS\Pro-Techno
npm run build
# на выходе: D:\DS\Pro-Techno\dist
```

Запустим бэк, который сам отдаст SPA + /api с одного порта:
```bash
# из C:\Users\Вадим\protechno-media-analyzer
$env:FRONTEND_DIST = "D:\DS\Pro-Techno\dist"
python -m backend.app.main
```

Если репозитории лежат рядом (`...\Pro-Techno` соседом с
`...\protechno-media-analyzer`) — переменную можно не задавать,
бэк сам подхватит `..\Pro-Techno\dist`.

Заходим на `http://<LAN-IP>:8000/`.

Бэк параметризируется:
- `BACKEND_HOST` (по умолчанию `0.0.0.0`)
- `BACKEND_PORT` (по умолчанию `8000`)
- `BACKEND_RELOAD` (`true`/`false`, по умолчанию `true`; в prod лучше `false`)
- `FRONTEND_DIST` (путь к собранному фронту)

## 3. Доступ из интернета — туннель

Когда нужен временный публичный URL (показать заказчику и т.п.).

### Cloudflare Tunnel (без аккаунта, одноразовый URL)

Установи `cloudflared` (https://github.com/cloudflare/cloudflared/releases),
а затем:
```bash
# prod-режим: один порт 8000
cloudflared tunnel --url http://localhost:8000

# dev-режим: фронт на 5173
cloudflared tunnel --url http://localhost:5173
```

Получишь URL вида `https://<random>.trycloudflare.com`. CORS на бэке уже
разрешён для `*.trycloudflare.com`.

### ngrok

```bash
ngrok http 8000     # prod
ngrok http 5173     # dev
```

Для `*.ngrok-free.app`/`*.ngrok.io` CORS тоже открыт.

## 4. Файрвол Windows

Если с телефона не открывается — Windows Defender блокирует входящие
подключения. Один раз разреши порт:
```powershell
# prod (8000)
New-NetFirewallRule -DisplayName "Pro-Techno backend" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
# dev (5173)
New-NetFirewallRule -DisplayName "Pro-Techno vite"    -Direction Inbound -Protocol TCP -LocalPort 5173 -Action Allow
```

## 5. Чек-лист перед хостингом

- [ ] Wi-Fi один и тот же (или машина в той же подсети, что устройства).
- [ ] `ipconfig` показывает корректный LAN-IP.
- [ ] `curl http://<LAN-IP>:8000/health/db` отвечает 200.
- [ ] CORS — на бэке стоит `allow_origin_regex` (см. `backend/app/main.py`).
- [ ] В dev: `vite.config.ts` → `server.host: true`. В prod: задан
      `FRONTEND_DIST`, `dist/index.html` существует.
