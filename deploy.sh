#!/bin/bash
# Самозапуск из временной копии, чтобы избежать перезаписи во время выполнения
if [[ -z "$DEPLOY_ORIGINAL_PID" ]]; then
    TMP_COPY=$(mktemp /tmp/deploy.XXXXXX.sh)
    cp "$0" "$TMP_COPY"
    chmod +x "$TMP_COPY"
    DEPLOY_ORIGINAL_PID=$$
    exec env DEPLOY_ORIGINAL_PID=$DEPLOY_ORIGINAL_PID "$TMP_COPY" "$@"
fi

REPO_URL=$(git config --get remote.origin.url)
if [ -z "$REPO_URL" ]; then
    echo "❌ Ошибка: Текущая папка не является Git-репозиторием!"
    exit 1
fi

TMP_DIR=$(mktemp -d)
CURRENT_DIR=$(pwd)
LOG_DIR="$CURRENT_DIR/logs"
BACKUP_DIR="$CURRENT_DIR/backup/$(date '+%Y-%m-%d_%H-%M-%S')"
LOG_FILE="$LOG_DIR/deploy_$(date '+%Y-%m-%d_%H-%M-%S').log"
mkdir -p "$LOG_DIR" "$BACKUP_DIR"

cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

echo "🔄 Начало деплоя $(date)" | tee -a "$LOG_FILE"
echo "🛑 Останавливаем сервер..." | tee -a "$LOG_FILE"
sudo docker stop app_server >>"$LOG_FILE" 2>&1 || echo "⚠ Контейнер не запущен" | tee -a "$LOG_FILE"

echo "📦 Получение списка веток с сервера..." | tee -a "$LOG_FILE"
REMOTE_BRANCHES_RAW=$(git ls-remote --heads "$REPO_URL" | awk '{print $2}' | sed 's|refs/heads/||' | sort -u)
REMOTE_BRANCHES=()

[[ "$REMOTE_BRANCHES_RAW" == *"master"* ]] && REMOTE_BRANCHES+=("master")
while IFS= read -r branch; do [[ $branch != "master" ]] && REMOTE_BRANCHES+=("$branch"); done <<< "$REMOTE_BRANCHES_RAW"

if [[ ${#REMOTE_BRANCHES[@]} -eq 1 ]]; then
    SELECTED_BRANCH="${REMOTE_BRANCHES[0]}"
    echo "✅ Единственная ветка: $SELECTED_BRANCH" | tee -a "$LOG_FILE"
else
    echo "Выберите ветку для деплоя:"
    select SELECTED_BRANCH in "${REMOTE_BRANCHES[@]}"; do [[ -n "$SELECTED_BRANCH" ]] && break; done
    echo "✅ Выбрана ветка: $SELECTED_BRANCH" | tee -a "$LOG_FILE"
fi

SELECTED_BRANCH=$(echo "$SELECTED_BRANCH" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

echo "🔄 Клонируем ветку $SELECTED_BRANCH..." | tee -a "$LOG_FILE"
git clone --depth 1 --branch "$SELECTED_BRANCH" "$REPO_URL" "$TMP_DIR" >>"$LOG_FILE" 2>&1 || {
    echo "❌ Ошибка: Не удалось клонировать ветку!" | tee -a "$LOG_FILE"; exit 1;
}

cd "$TMP_DIR"
DEPLOY_COMMIT=$(git rev-parse --short HEAD)
DEPLOY_DATE=$(git show -s --format=%ci HEAD)
DEPLOY_MESSAGE=$(git log -1 --pretty=%s)
echo "📦 Коммит: $DEPLOY_COMMIT ($DEPLOY_DATE)" | tee -a "$LOG_FILE"
echo "📝 Commit message: $DEPLOY_MESSAGE" | tee -a "$LOG_FILE"

cd "$CURRENT_DIR"
sudo rm -rf .git
cp -r "$TMP_DIR/.git" .git

change_permissions() {
    [[ -e "$1" ]] && sudo chown "$(whoami):$(whoami)" "$1" && sudo chmod u+w "$1"
}

echo "🔄 Обновление файлов:" | tee -a "$LOG_FILE"
BUILD_FRONTEND=false
BUILD_BACKEND=false

while read -r status file; do
    case $status in
        M|MM)
            echo "  * upd: $file" | tee -a "$LOG_FILE"
            change_permissions "$CURRENT_DIR/$file"
            mkdir -p "$BACKUP_DIR/$(dirname "$file")"
            cp "$CURRENT_DIR/$file" "$BACKUP_DIR/$file"
            cp "$TMP_DIR/$file" "$CURRENT_DIR/$file"
            ;;
        D)
            echo "  + new: $file" | tee -a "$LOG_FILE"
            cp "$TMP_DIR/$file" "$CURRENT_DIR/$file"
            ;;
        "??")
            if [[ $file == store/* || $file == backup/* ]]; then
                echo "   - skip: $file" | tee -a "$LOG_FILE"
            else
                echo "  - del: $file" | tee -a "$LOG_FILE"
                [[ -f "$CURRENT_DIR/$file" ]] && {
                    mkdir -p "$BACKUP_DIR/$(dirname "$file")"
                    cp "$CURRENT_DIR/$file" "$BACKUP_DIR/$file"
                }
                sudo rm -rf "$CURRENT_DIR/$file"
            fi
            ;;
    esac
    [[ $file == frontend* ]] && BUILD_FRONTEND=true
    [[ $file == backend/requirements.txt ]] && BUILD_BACKEND=true
done < <(git status --porcelain)

echo "🔄 Изменение прав доступа:" | tee -a "$LOG_FILE"
git diff --summary HEAD | while read -r line; do
    if [[ $line =~ \mode\ change\ 100([0-7]{3})\ =\>\ 100([0-7]{3})\ (.*) ]]; then
        old_mode=${BASH_REMATCH[1]}
        new_mode=${BASH_REMATCH[2]}
        file=${BASH_REMATCH[3]}
        sudo chmod "0$old_mode" "$file"
        echo "  - $file ($old_mode -> $new_mode)" | tee -a "$LOG_FILE"
    fi
done

if $BUILD_FRONTEND; then
    echo "🔄 Обновление фронтенда..." | tee -a "$LOG_FILE"
    make build_frontend >>"$LOG_FILE" 2>&1
else
    echo "🔶 Фронтенд без изменений." | tee -a "$LOG_FILE"
fi

if $BUILD_BACKEND; then
    echo "🔄 Обновление бэкенда..." | tee -a "$LOG_FILE"
    cd "$CURRENT_DIR/backend" || exit 1
    pip install -r requirements.txt --break-system-packages >>"$LOG_FILE" 2>&1
    sudo docker rm app_server --force
    sudo docker image rm server --force >>"$LOG_FILE" 2>&1
else
    echo "🔶 Бэкенд без изменений." | tee -a "$LOG_FILE"
fi

sudo chmod -R 777 "$CURRENT_DIR/store"
sudo chown -R "$(whoami):$(whoami)" "$CURRENT_DIR/store"

cd "$CURRENT_DIR" || exit 1
echo "🚀 Запускаем сервер..." | tee -a "$LOG_FILE"
make run_prod >>"$LOG_FILE" 2>&1

echo "✅ Деплой завершен! $(date)" | tee -a "$LOG_FILE"
