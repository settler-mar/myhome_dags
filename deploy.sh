#!/bin/bash

# Определяем URL репозитория
REPO_URL=$(git config --get remote.origin.url)
if [ -z "$REPO_URL" ]; then
    echo "❌ Ошибка: Текущая папка не является Git-репозиторием!"
    exit 1
fi

# Настройки
TMP_DIR=$(mktemp -d)
CURRENT_DIR=$(pwd)
LOG_DIR="$CURRENT_DIR/logs"
mkdir -p "$LOG_DIR"

# Генерация имени лога
LOG_FILE="$LOG_DIR/deploy_$(date '+%Y-%m-%d_%H-%M-%S').log"

# Очистка временной папки при выходе
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

echo "🔄 Начало деплоя $(date)" | tee -a "$LOG_FILE"

# Остановка сервера
echo "🛑 Останавливаем сервер..." | tee -a "$LOG_FILE"
sudo docker stop app_server >>"$LOG_FILE" 2>&1 || echo "⚠ Контейнер не запущен" | tee -a "$LOG_FILE"

# Клонируем последнюю версию
echo "🔄 Загружаем обновления..." | tee -a "$LOG_FILE"
git clone --depth 1 "$REPO_URL" "$TMP_DIR" >>"$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Ошибка: Не удалось клонировать репозиторий!" | tee -a "$LOG_FILE"
    exit 1
fi

# Получаем список игнорируемых файлов с помощью git ls-files
IGNORED_FILES=$(git ls-files --others --ignored --exclude-standard)

# Функция для записи изменений файлов в лог
log_file_change() {
    local file="$1"
    local action="$2"
    local size_before="$3"
    local size_after="$4"

    echo "$action: $file | Размер до: $size_before, Размер после: $size_after" >>"$LOG_FILE"
}

# Проверка и копирование файлов с rsync, получение изменений
echo "🔄 Обновление файлов..." | tee -a "$LOG_FILE"
rsync -a --dry-run --info=progress2 --exclude=".git" --exclude-from=<(echo "$IGNORED_FILES") "$TMP_DIR/" "$CURRENT_DIR/" | while read -r line; do
    if [[ "$line" =~ ^[[:space:]]*([^ ]+)[[:space:]]+([A-Za-z]+)[[:space:]]+([0-9]+)[[:space:]]+([0-9]+) ]]; then
        # Получаем имя файла, действие и размеры до/после
        file="${BASH_REMATCH[1]}"
        action="${BASH_REMATCH[2]}"
        size_before="${BASH_REMATCH[3]}"
        size_after="${BASH_REMATCH[4]}"

        # Логируем изменения
        log_file_change "$file" "$action" "$size_before" "$size_after"
    fi
done

# Копирование файлов без dry-run, чтобы применить изменения
echo "✅ Файлы обновлены!" | tee -a "$LOG_FILE"
rsync -a --exclude=".git" --exclude-from=<(echo "$IGNORED_FILES") "$TMP_DIR/" "$CURRENT_DIR/"

# Проверка на изменения во фронтенде и его сборка, если нужно
echo "🔍 Проверяем изменения во фронтенде..." | tee -a "$LOG_FILE"
BUILD_FRONTEND=false
cd "$CURRENT_DIR/frontend" || exit 1
TRACKED_FILES=$(git ls-files frontend)
for FILE in $TRACKED_FILES; do
    if ! diff -q "$CURRENT_DIR/$FILE" "$TMP_DIR/$FILE" >/dev/null 2>&1; then
        BUILD_FRONTEND=true
        echo "⚠ Изменен файл: $FILE" >>"$LOG_FILE"
    fi
done
cd "$CURRENT_DIR"

if [ "$BUILD_FRONTEND" = true ]; then
    echo "✅ Изменения найдены. Фронтенд будет пересобран." | tee -a "$LOG_FILE"
else
    echo "✅ Изменений нет. Билд фронтенда не требуется." | tee -a "$LOG_FILE"
fi

# Билд фронтенда, если были изменения
if [ "$BUILD_FRONTEND" = true ]; then
    echo "⚙ Запускаем билд фронтенда..." | tee -a "$LOG_FILE"
    cd "$CURRENT_DIR/frontend" || exit 1
    make build_frontend >>"$LOG_FILE" 2>&1
    cd "$CURRENT_DIR"
fi

# Запуск сервера
echo "🚀 Запускаем сервер..." | tee -a "$LOG_FILE"
make run_prod >>"$LOG_FILE" 2>&1

echo "✅ Деплой завершен! $(date)" | tee -a "$LOG_FILE"
