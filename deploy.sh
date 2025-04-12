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
BACKUP_ROOT="$CURRENT_DIR/backup"
BACKUP_DIR="$BACKUP_ROOT/$(date '+%Y-%m-%d_%H-%M-%S')"
mkdir -p "$LOG_DIR" "$BACKUP_DIR"

# Генерация имени лога
LOG_FILE="$LOG_DIR/deploy_$(date '+%Y-%m-%d_%H-%M-%S').log"

# Очистка временной папки при выходе
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

echo "🔄 Начало деплоя $(date)" | tee -a "$LOG_FILE"

# Остановка сервера
echo "🛑 Останавливаем сервер..." | tee -a "$LOG_FILE"
sudo docker stop app_server >>"$LOG_FILE" 2>&1 || echo "⚠ Контейнер не запущен" | tee -a "$LOG_FILE"

# Получение и выбор ветки
# Получение удалённых веток
echo "📦 Получение списка удалённых веток..." | tee -a "$LOG_FILE"
git fetch --all --prune >>"$LOG_FILE" 2>&1
REMOTE_BRANCHES_RAW=$(git branch -r | grep -v 'HEAD\|->' | sed 's|origin/||' | sort -u)

# Сортировка: master — первая
REMOTE_BRANCHES=()
if echo "$REMOTE_BRANCHES_RAW" | grep -Fxq "master"; then
    REMOTE_BRANCHES+=("master")
fi
while IFS= read -r branch; do
    [[ $branch != "master" ]] && REMOTE_BRANCHES+=("$branch")
done <<< "$REMOTE_BRANCHES_RAW"

# Выбор ветки
if [ "${#REMOTE_BRANCHES[@]}" -eq 1 ]; then
    SELECTED_BRANCH="${REMOTE_BRANCHES[0]}"
    echo "✅ Единственная ветка: $SELECTED_BRANCH" | tee -a "$LOG_FILE"
else
    echo "Выберите ветку для деплоя:"
    select SELECTED_BRANCH in "${REMOTE_BRANCHES[@]}"; do
        [ -n "$SELECTED_BRANCH" ] && break
    done
    echo "✅ Выбрана ветка: $SELECTED_BRANCH" | tee -a "$LOG_FILE"
fi

# Клонируем ветку
echo "🔄 Клонируем ветку $SELECTED_BRANCH..." | tee -a "$LOG_FILE"
git clone --depth 1 --branch "$SELECTED_BRANCH" "$REPO_URL" "$TMP_DIR" >>"$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Ошибка: Не удалось клонировать ветку!" | tee -a "$LOG_FILE"
    exit 1
fi

cd "$TMP_DIR"
DEPLOY_COMMIT=$(git rev-parse --short HEAD)
DEPLOY_DATE=$(git show -s --format=%ci HEAD)
DEPLOY_MESSAGE=$(git log -1 --pretty=%s)

echo "📦 Коммит для деплоя: $DEPLOY_COMMIT ($DEPLOY_DATE)" | tee -a "$LOG_FILE"
echo "📝 $DEPLOY_MESSAGE" | tee -a "$LOG_FILE"

# Переносим .git
cd "$CURRENT_DIR"
rm -rf .git
cp -r "$TMP_DIR/.git" .git

change_permissions() {
    local file="$1"
    if [ -e "$file" ]; then
        sudo chown "$(whoami):$(whoami)" "$file"
        sudo chmod u+w "$file"
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
            mkdir -p "$BACKUP_DIR/$(dirname "$file")"
            cp "$CURRENT_DIR/$file" "$BACKUP_DIR/$file"
            cp "$TMP_DIR/$file" "$CURRENT_DIR/$file"
            ;;
        "D")
            echo "  + new: $file" | tee -a "$LOG_FILE"
            cp "$TMP_DIR/$file" "$CURRENT_DIR/$file"
            ;;
        "??")
            if [[ $file == store/* ]]; then
                echo "   - skip (store): $file" | tee -a "$LOG_FILE"
            else
                echo "  - del: $file" | tee -a "$LOG_FILE"
                if [ -f "$CURRENT_DIR/$file" ]; then
                    mkdir -p "$BACKUP_DIR/$(dirname "$file")"
                    cp "$CURRENT_DIR/$file" "$BACKUP_DIR/$file"
                fi
                sudo rm -rf "$CURRENT_DIR/$file"
            fi
            ;;
    esac
    [[ $file == frontend* ]] && BUILD_FRONTEND=true
    [[ $file == backend/requirements.txt ]] && BUILD_BACKEND=true
done < <(git status --porcelain)

echo "🔄 Изменение прав доступа:" | tee -a "$LOG_FILE"
changes=$(git diff --summary HEAD)
while IFS= read -r line; do
    if [[ $line =~ mode\ change\ 100([0-7]{3})\ =>\ 100([0-7]{3})\ (.*) ]]; then
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
    make build_frontend >>"$LOG_FILE" 2>&1
else
    echo "🔶 Изменений во фронтенде нет." | tee -a "$LOG_FILE"
fi

if [ "$BUILD_BACKEND" = true ]; then
    echo "🔄 Обновление зависимостей бэкенда..." | tee -a "$LOG_FILE"
    cd "$CURRENT_DIR/backend" || exit 1
    pip install -r requirements.txt --break-system-packages >>"$LOG_FILE" 2>&1
    sudo docker rm app_server --force
    sudo docker image rm server --force >>"$LOG_FILE" 2>&1
else
    echo "🔶 Изменений в бэкенде нет." | tee -a "$LOG_FILE"
fi

# set permissions and ownership in store dir for all files
sudo chmod -R 777 "$CURRENT_DIR/store"
sudo chown -R "$(whoami):$(whoami)" "$CURRENT_DIR/store"

# Запуск сервера
cd "$CURRENT_DIR" || exit 1
echo "🚀 Запускаем сервер..." | tee -a "$LOG_FILE"
make run_prod >>"$LOG_FILE" 2>&1

echo "✅ Деплой завершен! $(date)" | tee -a "$LOG_FILE"
