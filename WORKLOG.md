# Журнал работ (Work Log)

Хронология выполненных шагов. Время — America/Toronto (UTC−5).

- **2026-11-22 09:35** — Прочитано ТЗ (`docs/TZ_uchebny_sait.md`), определён объём MVP (этап 1).
- **2026-11-22 09:40** — Создан venv, установлены Django 5.2, pytest, playwright, argon2; скачаны self-hosted HTMX 2.0.4 и шрифт Nunito (cyrillic+latin).
- **2026-11-22 09:50** — Каркас проекта: `config/`, 7 приложений, настройки (SQLite/PostgreSQL), CSP middleware.
- **2026-11-22 10:00** — Модели и сервисы: accounts (семья, родитель, ребёнок, картинный пароль), content, srs (SM-2 + interleaving), learning (mastery, adaptive, checkers, player), rewards (звёзды, значки, серии), missions (сборщик миссии + диагностика), parents (кабинет).
- **2026-11-22 10:40** — Создан `DECISIONS.md` с бэкфиллом решений D-001…D-014.
- **2026-11-22 10:45** — Команды `import_content`, `seed_demo`; инициализирован git, добавлен remote GitHub, ТЗ скопировано в `docs/`.
