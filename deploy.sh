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

git reset
git add .

# Создаем список файлов в текущей и новой версии
echo "📋 Создаем списки файлов из новой версии..." | tee -a "$LOG_FILE"
cd "$TMP_DIR"
python3 dist_list.py
cp file_list.txt "$CURRENT_DIR/file_list.txt"
cd "$CURRENT_DIR"

# Формируем список задач
echo "📋 Создаем списки файлов действий..." | tee -a "$LOG_FILE"
python3 dist_list.py

# Проверка и копирование файлов с rsync, получение изменений
echo "🔄 Обновление файлов..." | tee -a "$LOG_FILE"
BUILD_FRONTEND=false
BUILD_BACKEND=false
while IFS= read -r line
do
    action=$(echo $line | cut -d ' ' -f 1)
    file=$(echo $line | cut -d ' ' -f 2)
    case $action in
        "d")
            echo "🗑 Удаление файла: $file" | tee -a "$LOG_FILE"
            rm -rf "$CURRENT_DIR/$file"
            ;;
        "u")
            echo "🔄 Обновление файла: $file" | tee -a "$LOG_FILE"
            cp "$TMP_DIR/$file" "$CURRENT_DIR/$file"
            ;;
        "c")
            echo "📝 Создание файла: $file" | tee -a "$LOG_FILE"
            cp "$TMP_DIR/$file" "$CURRENT_DIR/$file"
            ;;
    esac
    if [[ $action == "u" || $action == "c" ]] && [[ $file == "frontend"* ]]; then
        BUILD_FRONTEND=true
    fi
    if [[ $action == "u" || $action == "c" ]] && [[ $file == "backend/requirements.txt" ]]; then
        BUILD_BACKEND=true
    fi
done < file_to_process.txt
git reset
rm file_to_process.txt || true
rm file_list.txt || true

if [ "$BUILD_FRONTEND" = true ]; then
    echo "✅ Изменения найдены. Фронтенд будет пересобран." | tee -a "$LOG_FILE"
else
    echo "✅ Изменений нет. Билд фронтенда не требуется." | tee -a "$LOG_FILE"
fi


if [ "$BUILD_BACKEND" = true ]; then
    echo "✅ Изменения найдены. Бэкенд будет пересобран." | tee -a "$LOG_FILE"
else
    echo "✅ Изменений нет. Билд бэкенда не требуется." | tee -a "$LOG_FILE"
fi

# Билд бэкенда, если были изменения
if [ "$BUILD_BACKEND" = true ]; then
    echo "⚙ Запускаем билд бэкенда..." | tee -a "$LOG_FILE"
    cd "$CURRENT_DIR/backend" || exit 1
    pip install -r requirements.txt --break-system-packages>>"$LOG_FILE" 2>&1
    sudo docker rm app_server --force
    sudo docker image rm server --force >>"$LOG_FILE" 2>&1
fi

# Билд фронтенда, если были изменения
if [ "$BUILD_FRONTEND" = true ]; then
    echo "⚙ Запускаем билд фронтенда..." | tee -a "$LOG_FILE"
     cd "$CURRENT_DIR" || exit 1
    make build_frontend >>"$LOG_FILE" 2>&1
    cd "$CURRENT_DIR"
fi

# Запуск сервера
echo "🚀 Запускаем сервер..." | tee -a "$LOG_FILE"
make run_prod >>"$LOG_FILE" 2>&1

echo "✅ Деплой завершен! $(date)" | tee -a "$LOG_FILE"
