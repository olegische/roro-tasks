#!/bin/bash

# Проверка наличия API ключа
if [ -z "$OPENAI_API_KEY" ]; then
    echo "Ошибка: Не установлена переменная окружения OPENAI_API_KEY" >&2
    exit 1
fi

# Проверка аргументов
if [ "$#" -ne 2 ]; then
    echo "Использование: $0 'document_analysis_json' 'user_query'" >&2
    exit 1
fi

DOCUMENT_ANALYSIS="$1"
USER_QUERY="$2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPT_FILE="$SCRIPT_DIR/../prompts/dsl_generator.prompt"

# Проверка наличия файла с промптом
if [ ! -f "$PROMPT_FILE" ]; then
    echo "Ошибка: Файл с промптом не найден: $PROMPT_FILE" >&2
    exit 1
fi

# Проверка валидности JSON анализа документа
if ! echo "$DOCUMENT_ANALYSIS" | jq '.' >/dev/null 2>&1; then
    echo "Ошибка: Переданный анализ документа не является валидным JSON" >&2
    exit 1
fi

# Чтение промпта из файла
SYSTEM_PROMPT=$(cat "$PROMPT_FILE")

# Формирование контекста для модели
CONTEXT=$(cat << EOF
Анализ документа:
$(echo "$DOCUMENT_ANALYSIS" | jq -r '.')

Запрос пользователя:
$USER_QUERY
EOF
)

# Формирование JSON для запроса к API
REQUEST_JSON=$(cat << EOF
{
  "model": "gpt-4-turbo-preview",
  "messages": [
    {
      "role": "system",
      "content": $(echo "$SYSTEM_PROMPT" | jq -R -s '.')
    },
    {
      "role": "user",
      "content": $(echo "$CONTEXT" | jq -R -s '.')
    }
  ],
  "response_format": {
    "type": "json_object"
  },
  "temperature": 0.2
}
EOF
)

# Отправка запроса к API
RESPONSE=$(curl -s -X POST "https://api.openai.com/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -d "$REQUEST_JSON")

# Проверка ответа на наличие ошибок
if echo "$RESPONSE" | jq -e '.error' >/dev/null; then
    ERROR_MSG=$(echo "$RESPONSE" | jq -r '.error.message')
    echo "Ошибка при генерации DSL: $ERROR_MSG" >&2
    exit 1
fi

# Извлечение результата
DSL_RESULT=$(echo "$RESPONSE" | jq -r '.choices[0].message.content')

# Проверка валидности YAML
if ! echo "$DSL_RESULT" | yq eval '.' >/dev/null 2>&1; then
    echo "Ошибка: Сгенерированный DSL не является валидным YAML" >&2
    exit 1
fi

# Проверка наличия необходимых секций в DSL
REQUIRED_SECTIONS=("intersection_metric" "extraction_area" "type" "params")
for section in "${REQUIRED_SECTIONS[@]}"; do
    if ! echo "$DSL_RESULT" | yq eval "has(\"$section\")" | grep -q true; then
        echo "Ошибка: В DSL отсутствует обязательная секция '$section'" >&2
        exit 1
    fi
done

# Проверка наличия якорей
if ! echo "$DSL_RESULT" | yq eval '.params.attributes[].params.anchors' | grep -q .; then
    echo "Ошибка: В DSL отсутствуют якоря" >&2
    exit 1
fi

# Вывод результата
echo "$DSL_RESULT"
