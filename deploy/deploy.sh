#!/usr/bin/env bash
# Выкладка релиза: ./deploy.sh <git-tag>. ЗАПУСКАТЬ ВРУЧНУЮ на сервере (не автоматизировано из CI).
set -euo pipefail
TAG="${1:?usage: deploy.sh <tag>}"
ROOT=/srv/school-site
REL="$ROOT/releases/$TAG"
set -a; . "$ROOT/.env"; set +a
mkdir -p "$ROOT/releases" "$ROOT/backups"
pg_dump -Fc -h 127.0.0.1 -U "$POSTGRES_USER" "$POSTGRES_DB" > "$ROOT/backups/pre-$TAG-$(date +%F-%H%M).dump"
git clone --depth 1 --branch "$TAG" https://github.com/RomanKeter/school-site.git "$REL"
"$ROOT/venv/bin/pip" install -q -r "$REL/requirements.txt"
cd "$REL"
"$ROOT/venv/bin/python" manage.py migrate --noinput
"$ROOT/venv/bin/python" manage.py collectstatic --noinput
ln -sfn "$REL" "$ROOT/current"
sudo systemctl reload school-site
echo "Готово: $TAG. Откат: ln -sfn $ROOT/releases/<prev> $ROOT/current && sudo systemctl reload school-site"
