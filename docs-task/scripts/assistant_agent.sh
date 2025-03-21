#!/bin/bash

# Проверка наличия необходимых утилит
command -v curl >/dev/null 2>&1 || { echo "Требуется curl" >&2; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "Требуется jq" >&2; exit 1; }

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

# Функция для логирования
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Функция обработки ошибок
handle_error() {
    log "ОШИБКА: $1"
    exit 1
}

# Функция для создания ассистента
create_assistant() {
    local document_analyzer_prompt=$(cat "$SCRIPT_DIR/../prompts/document_analyzer.prompt")
    local dsl_generator_prompt=$(cat "$SCRIPT_DIR/../prompts/dsl_generator.prompt")
    
    local instructions=$(cat <<EOF
Ты - эксперт по анализу документов и созданию DSL шаблонов. Твоя задача:

1. Анализ документа:
$document_analyzer_prompt

2. Генерация DSL:
$dsl_generator_prompt

Используй code_interpreter для обработки изображений и создания точных координат.
EOF
)

    local response=$(curl -s -X POST "https://api.openai.com/v1/assistants" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $OPENAI_API_KEY" \
        -H "OpenAI-Beta: assistants=v2" \
        -d "{
            \"name\": \"Document DSL Generator\",
            \"description\": \"Анализирует документы и создает DSL шаблоны для извлечения данных\",
            \"model\": \"gpt-4-vision-preview\",
            \"instructions\": \"$instructions\",
            \"tools\": [{\"type\": \"code_interpreter\"}]
        }")

    echo "$response" | jq -r '.id'
}

# Функция для создания треда
create_thread() {
    local response=$(curl -s -X POST "https://api.openai.com/v1/threads" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $OPENAI_API_KEY" \
        -H "OpenAI-Beta: assistants=v2" \
        -d "{}")

    echo "$response" | jq -r '.id'
}

# Функция для загрузки файла
upload_file() {
    local file_path="$1"
    local purpose="$2"

    local response=$(curl -s -X POST "https://api.openai.com/v1/files" \
        -H "Authorization: Bearer $OPENAI_API_KEY" \
        -F "purpose=$purpose" \
        -F "file=@$file_path")

    echo "$response" | jq -r '.id'
}

# Функция для добавления сообщения в тред
add_message() {
    local thread_id="$1"
    local content="$2"
    local file_id="$3"

    local message_data="{
        \"role\": \"user\",
        \"content\": \"$content\""

    if [ ! -z "$file_id" ]; then
        message_data="$message_data,
        \"attachments\": [{
            \"file_id\": \"$file_id\",
            \"tools\": [\"code_interpreter\"]
        }]"
    fi

    message_data="$message_data }"

    local response=$(curl -s -X POST "https://api.openai.com/v1/threads/$thread_id/messages" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $OPENAI_API_KEY" \
        -H "OpenAI-Beta: assistants=v2" \
        -d "$message_data")

    echo "$response" | jq -r '.id'
}

# Функция для запуска выполнения
run_assistant() {
    local thread_id="$1"
    local assistant_id="$2"

    local response=$(curl -s -X POST "https://api.openai.com/v1/threads/$thread_id/runs" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $OPENAI_API_KEY" \
        -H "OpenAI-Beta: assistants=v2" \
        -d "{
            \"assistant_id\": \"$assistant_id\"
        }")

    echo "$response" | jq -r '.id'
}

# Функция для проверки статуса выполнения
check_run_status() {
    local thread_id="$1"
    local run_id="$2"

    local response=$(curl -s -X GET "https://api.openai.com/v1/threads/$thread_id/runs/$run_id" \
        -H "Authorization: Bearer $OPENAI_API_KEY" \
        -H "OpenAI-Beta: assistants=v2")

    echo "$response" | jq -r '.status'
}

# Функция для получения сообщений
get_messages() {
    local thread_id="$1"

    local response=$(curl -s -X GET "https://api.openai.com/v1/threads/$thread_id/messages" \
        -H "Authorization: Bearer $OPENAI_API_KEY" \
        -H "OpenAI-Beta: assistants=v2")

    echo "$response" | jq -r '.data[0].content[0].text.value'
}

# Основной процесс
main() {
    # 1. Создание ассистента
    log "Создание ассистента..."
    ASSISTANT_ID=$(create_assistant)
    [ -z "$ASSISTANT_ID" ] && handle_error "Не удалось создать ассистента"

    # 2. Создание треда
    log "Создание треда..."
    THREAD_ID=$(create_thread)
    [ -z "$THREAD_ID" ] && handle_error "Не удалось создать тред"

    # 3. Загрузка документа
    log "Загрузка документа..."
    FILE_ID=$(upload_file "$DOCUMENT_PATH" "assistants")
    [ -z "$FILE_ID" ] && handle_error "Не удалось загрузить файл"

    # 4. Добавление сообщения с документом и запросом
    log "Отправка сообщения..."
    MESSAGE_ID=$(add_message "$THREAD_ID" "$USER_QUERY" "$FILE_ID")
    [ -z "$MESSAGE_ID" ] && handle_error "Не удалось отправить сообщение"

    # 5. Запуск ассистента
    log "Запуск обработки..."
    RUN_ID=$(run_assistant "$THREAD_ID" "$ASSISTANT_ID")
    [ -z "$RUN_ID" ] && handle_error "Не удалось запустить обработку"

    # 6. Ожидание завершения
    log "Ожидание результата..."
    while true; do
        STATUS=$(check_run_status "$THREAD_ID" "$RUN_ID")
        case "$STATUS" in
            "completed")
                break
                ;;
            "failed"|"cancelled"|"expired")
                handle_error "Выполнение завершилось с ошибкой: $STATUS"
                ;;
            *)
                sleep 1
                ;;
        esac
    done

    # 7. Получение результата
    log "Получение результата..."
    RESULT=$(get_messages "$THREAD_ID")
    echo "$RESULT"

    # 8. Очистка
    log "Удаление временных файлов..."
    curl -s -X DELETE "https://api.openai.com/v1/files/$FILE_ID" \
        -H "Authorization: Bearer $OPENAI_API_KEY" \
        -H "OpenAI-Beta: assistants=v2" >/dev/null

    log "Готово"
}

# Запуск основного процесса
main
