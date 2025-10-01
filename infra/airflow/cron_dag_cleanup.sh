#!/bin/bash
#
# Автоматический cron job для очистки осиротевших DAG файлов
# Рекомендуемое расписание: каждые 6 часов
#
# Добавить в crontab внутри контейнера Airflow:
# 0 */6 * * * /opt/airflow/scripts/cron_dag_cleanup.sh >> /opt/airflow/logs/dag_cleanup.log 2>&1
#

# Настройки
DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings}"
DJANGO_PROJECT_PATH="${DJANGO_PROJECT_PATH:-/opt/airflow/backend}"
MAX_FILES_PER_RUN="${MAX_FILES_PER_RUN:-20}"
LOG_FILE="/opt/airflow/logs/dag_cleanup_$(date +%Y%m%d_%H%M%S).log"

# Логирование
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "🚀 Запуск автоматической очистки осиротевших DAG файлов"
log "📋 Конфигурация: MAX_FILES=$MAX_FILES_PER_RUN, PROJECT=$DJANGO_PROJECT_PATH"

# Переходим в директорию проекта Django
cd "$DJANGO_PROJECT_PATH" || {
    log "❌ ОШИБКА: Не удалось перейти в директорию $DJANGO_PROJECT_PATH"
    exit 1
}

# Проверяем наличие manage.py
if [ ! -f "manage.py" ]; then
    log "❌ ОШИБКА: Файл manage.py не найден в $DJANGO_PROJECT_PATH"
    exit 1
fi

# Экспортируем Django settings
export DJANGO_SETTINGS_MODULE

# Запускаем команду очистки
log "🧹 Выполнение команды очистки..."

# Сначала dry-run для проверки
python manage.py cleanup_orphaned_dags \
    --dry-run \
    --max-files "$MAX_FILES_PER_RUN" \
    >> "$LOG_FILE" 2>&1

DRY_RUN_EXIT_CODE=$?

if [ $DRY_RUN_EXIT_CODE -ne 0 ]; then
    log "❌ ОШИБКА: Dry-run завершился с кодом $DRY_RUN_EXIT_CODE"
    log "📋 Подробности в логе: $LOG_FILE"
    exit $DRY_RUN_EXIT_CODE
fi

log "✅ Dry-run успешно завершен, выполняем реальную очистку..."

# Реальное удаление
python manage.py cleanup_orphaned_dags \
    --force \
    --max-files "$MAX_FILES_PER_RUN" \
    >> "$LOG_FILE" 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    log "✅ Автоматическая очистка успешно завершена"
else
    log "❌ ОШИБКА: Очистка завершилась с кодом $EXIT_CODE"
    log "📋 Подробности в логе: $LOG_FILE"
    
    # Отправляем алерт при критической ошибке (если настроено)
    if [ -n "$SLACK_WEBHOOK_URL" ] && command -v curl >/dev/null 2>&1; then
        log "📧 Отправка алерта в Slack..."
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"🚨 CRITICAL: Automated DAG cleanup failed with exit code $EXIT_CODE. Check logs: $LOG_FILE\"}" \
            "$SLACK_WEBHOOK_URL" >> "$LOG_FILE" 2>&1
    fi
fi

# Очистка старых логов (старше 7 дней)
find /opt/airflow/logs -name "dag_cleanup_*.log" -type f -mtime +7 -delete 2>/dev/null

log "🏁 Завершение автоматической очистки"
exit $EXIT_CODE
