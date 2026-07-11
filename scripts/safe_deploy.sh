#!/usr/bin/env bash
# Безопасный деплой: обновляет код из GitHub и перезапускает сервис
# только когда нет активной проверки товарного фида.
#
# Использование на сервере:
#   bash scripts/safe_deploy.sh          # pull + restart, если безопасно
#   bash scripts/safe_deploy.sh pull     # только git pull (не прерывает процесс)
#   bash scripts/safe_deploy.sh restart   # перезапуск, если проверка не идёт
#   bash scripts/safe_deploy.sh status    # показать активные проверки
#
# Перезапуск (если не systemd):
#   RESTART_CMD="systemctl restart mcz_health" bash scripts/safe_deploy.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DB_PATH="${DB_PATH:-$ROOT/data/catalog_monitor.db}"
RESTART_CMD="${RESTART_CMD:-systemctl restart mcz_health}"

mode="${1:-deploy}"

has_running_product_check() {
  python3 - "$DB_PATH" <<'PY'
import sqlite3
import sys
from pathlib import Path

db_path = Path(sys.argv[1])
if not db_path.exists():
    sys.exit(1)

conn = sqlite3.connect(db_path)
row = conn.execute(
    """
    SELECT id, started_at
    FROM feed_checks
    WHERE status = 'running' AND feed_type = 'product'
    ORDER BY id DESC
    LIMIT 1
    """
).fetchone()
conn.close()

if row:
    print(f"product#{row[0]} started_at={row[1]}")
    sys.exit(0)
sys.exit(1)
PY
}

show_status() {
  if [[ ! -f "$DB_PATH" ]]; then
    echo "БД не найдена: $DB_PATH"
    exit 0
  fi
  echo "Активные проверки:"
  python3 - "$DB_PATH" <<'PY'
import sqlite3
import sys
from pathlib import Path

conn = sqlite3.connect(sys.argv[1])
rows = conn.execute(
    """
    SELECT id, feed_type, status, started_at
    FROM feed_checks
    WHERE status = 'running'
    ORDER BY id DESC
    """
).fetchall()
conn.close()

if not rows:
    print("  нет")
else:
    for row in rows:
        print(f"  #{row[0]} {row[1]} {row[2]} с {row[3]}")
PY
}

git_pull() {
  echo "=== git pull ==="
  git fetch origin main
  git pull --ff-only origin main
  echo "Код обновлён до: $(git rev-parse --short HEAD)"
}

safe_restart() {
  if has_running_product_check; then
    echo ""
    echo "Товарная проверка ещё выполняется — перезапуск пропущен."
    echo "Код на диске уже обновлён (если был pull)."
    echo "Повторите позже:"
    echo "  bash scripts/safe_deploy.sh restart"
    return 1
  fi

  echo "=== restart ==="
  eval "$RESTART_CMD"
  echo "Сервис перезапущен."
}

case "$mode" in
  pull)
    git_pull
    ;;
  restart)
    safe_restart
    ;;
  status)
    show_status
    ;;
  deploy)
    git_pull
    safe_restart || true
    ;;
  *)
    echo "Неизвестный режим: $mode"
    echo "Режимы: deploy | pull | restart | status"
    exit 1
    ;;
esac
