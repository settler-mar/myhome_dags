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

# переносим .git в текущую версию
echo "🔄 Переносим .git в текущую версию..." | tee -a "$LOG_FILE"
cd "$CURRENT_DIR"
rm -rf "$CURRENT_DIR/.git"
cp -r "$TMP_DIR/.git" "$CURRENT_DIR/.git"

change_permissions() {
  local file="$1"
  if [ -e "$file" ]; then
    sudo chown "$(whoami):$(whoami)" "$file"  # Меняем владельца на текущего пользователя
    sudo chmod u+w "$file"  # Даем право на запись
  fi
}

# Проверка и копирование файлов с rsync, получение изменений
echo "🔄 Обновление файлов:" | tee -a "$LOG_FILE"
BUILD_FRONTEND=false
BUILD_BACKEND=false
while read -r status file; do
    case $status in
        "M"|"MM")
            echo "  * upd: $file" | tee -a "$LOG_FILE"
            change_permissions "$CURRENT_DIR/$file"
            cp "$TMP_DIR/$file" "$CURRENT_DIR/$file"
            ;;
        "D")
            echo "  + crt: $file" | tee -a "$LOG_FILE"
            cp "$TMP_DIR/$file" "$CURRENT_DIR/$file"
            ;;
        "??")
            echo "  - del: $file" | tee -a "$LOG_FILE"
            sudo rm -rf "$CURRENT_DIR/$file"
            ;;
    esac
    if [[ $file == "frontend"* ]]; then
        BUILD_FRONTEND=true
    fi
    if [[ $file == "backend/requirements.txt" ]]; then
        BUILD_BACKEND=true
    fi
done < <(git status --porcelain)

echo "🔄 Изменение прав доступа:" | tee -a "$LOG_FILE"
changes=$(git diff --summary HEAD)
while IFS= read -r line; do
    # Проверяем, изменились ли права доступа (mode change 100644 => 100755 file)
    if [[ $line =~ \mode\ change\ 100([0-7]{3})\ =\>\ 100([0-7]{3})\ (.*) ]]; then
        old_mode=${BASH_REMATCH[1]}
        new_mode=${BASH_REMATCH[2]}
        file=${BASH_REMATCH[3]}

        # Преобразуем числовой режим в восьмеричный формат
        sudo chmod "0$old_mode" "$file"
        echo "  - $file ($old_mode -> $new_mode)"
    fi
done <<< "$changes"

if [ "$BUILD_FRONTEND" = true ]; then
    echo "🔄 Обновление зависимостей фронтенда..." | tee -a "$LOG_FILE"
else
    echo "🔶 Изменений в фронтенде не найдено." | tee -a "$LOG_FILE"
fi
# Билд фронтенда, если были изменения
if [ "$BUILD_FRONTEND" = true ]; then
     cd "$CURRENT_DIR" || exit 1
    make build_frontend >>"$LOG_FILE" 2>&1
    cd "$CURRENT_DIR"
fi


if [ "$BUILD_BACKEND" = true ]; then
    echo "🔄 Обновление зависимостей бэкенда..." | tee -a "$LOG_FILE"
else
    echo "🔶 Изменений в зависимостях бэкенде не найдено." | tee -a "$LOG_FILE"
fi
# Билд бэкенда, если были изменения
if [ "$BUILD_BACKEND" = true ]; then
    cd "$CURRENT_DIR/backend" || exit 1
    pip install -r requirements.txt --break-system-packages>>"$LOG_FILE" 2>&1
    sudo docker rm app_server --force
    sudo docker image rm server --force >>"$LOG_FILE" 2>&1
fi

# set permissions and ownership in store dir for all files
sudo chmod -R 777 "$CURRENT_DIR/store"
sudo chown -R "$(whoami):$(whoami)" "$CURRENT_DIR/store"

# Запуск сервера
cd "$CURRENT_DIR" || exit 1
echo "🚀 Запускаем сервер..." | tee -a "$LOG_FILE"
make run_prod >>"$LOG_FILE" 2>&1

echo "✅ Деплой завершен! $(date)" | tee -a "$LOG_FILE"
