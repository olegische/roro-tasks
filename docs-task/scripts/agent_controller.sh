#!/bin/bash

# Проверка наличия необходимых утилит
command -v curl >/dev/null 2>&1 || { echo "Требуется curl" >&2; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "Требуется jq" >&2; exit 1; }
command -v yq >/dev/null 2>&1 || { echo "Требуется yq" >&2; exit 1; }

# Проверка наличия API ключа
if [ -z "$OPENAI_API_KEY" ]; then
    echo "Ошибка: Не установлена переменная окружения OPENAI_API_KEY"
    exit 1
fi

# Проверка аргументов
if [ "$#" -ne 2 ]; then
    echo "Использование: $0 path/to/document.jpg 'запрос пользователя'"
    exit 1
fi

DOCUMENT_PATH="$1"
USER_QUERY="$2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Проверка существования файла
if [ ! -f "$DOCUMENT_PATH" ]; then
    echo "Ошибка: Файл $DOCUMENT_PATH не существует"
    exit 1
fi

# Функция для логирования
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Функция обработки ошибок
handle_error() {
    log "ОШИБКА: $1"
    exit 1
}

# 1. Загрузка документа
log "Загрузка документа..."
UPLOAD_RESULT=$("$SCRIPT_DIR/document_uploader.sh" "$DOCUMENT_PATH") || handle_error "Ошибка загрузки документа"
FILE_ID=$(echo "$UPLOAD_RESULT" | jq -r '.id')

if [ -z "$FILE_ID" ]; then
    handle_error "Не удалось получить ID файла"
fi

# 2. Анализ документа
log "Анализ документа..."
ANALYSIS_RESULT=$("$SCRIPT_DIR/document_analyzer.sh" "$FILE_ID") || handle_error "Ошибка анализа документа"

# 3. Генерация DSL шаблона
log "Генерация DSL шаблона..."
DSL_RESULT=$("$SCRIPT_DIR/dsl_generator.sh" "$ANALYSIS_RESULT" "$USER_QUERY") || handle_error "Ошибка генерации DSL"

# 4. Извлечение данных
log "Извлечение данных..."
EXTRACTION_RESULT=$("$SCRIPT_DIR/data_extractor.sh" "$FILE_ID" "$DSL_RESULT") || handle_error "Ошибка извлечения данных"

# 5. Вывод результата
log "Результат:"
echo "$EXTRACTION_RESULT" | jq '.'

# Очистка
log "Удаление временных файлов..."
curl -X DELETE "https://api.openai.com/v1/files/$FILE_ID" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "OpenAI-Beta: assistants=v2" \
  >/dev/null 2>&1

log "Готово"
