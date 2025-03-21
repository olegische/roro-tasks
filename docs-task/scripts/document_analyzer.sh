#!/bin/bash

# Проверка наличия API ключа
if [ -z "$OPENAI_API_KEY" ]; then
    echo "Ошибка: Не установлена переменная окружения OPENAI_API_KEY" >&2
    exit 1
fi

# Проверка аргументов
if [ "$#" -ne 1 ]; then
    echo "Использование: $0 file_id" >&2
    exit 1
fi

FILE_ID="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPT_FILE="$SCRIPT_DIR/../prompts/document_analyzer.prompt"

# Проверка наличия файла с промптом
if [ ! -f "$PROMPT_FILE" ]; then
    echo "Ошибка: Файл с промптом не найден: $PROMPT_FILE" >&2
    exit 1
fi

# Чтение промпта из файла
SYSTEM_PROMPT=$(cat "$PROMPT_FILE")

# Получение содержимого файла в base64
FILE_CONTENT=$(curl -s "https://api.openai.com/v1/files/$FILE_ID/content" \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -H "OpenAI-Beta: assistants=v2")

if [ $? -ne 0 ]; then
    echo "Ошибка: Не удалось получить содержимое файла" >&2
    exit 1
fi

# Формирование JSON для запроса к API
REQUEST_JSON=$(cat << EOF
{
  "model": "gpt-4-vision-preview",
  "messages": [
    {
      "role": "system",
      "content": $(echo "$SYSTEM_PROMPT" | jq -R -s '.')
    },
    {
      "role": "user",
      "content": [
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/jpeg;base64,$FILE_CONTENT"
          }
        }
      ]
    }
  ],
  "max_tokens": 4096
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
    echo "Ошибка при анализе документа: $ERROR_MSG" >&2
    exit 1
fi

# Извлечение результата анализа
ANALYSIS_RESULT=$(echo "$RESPONSE" | jq -r '.choices[0].message.content')

# Проверка валидности JSON результата
if ! echo "$ANALYSIS_RESULT" | jq '.' >/dev/null 2>&1; then
    echo "Ошибка: Результат анализа не является валидным JSON" >&2
    exit 1
fi

# Проверка наличия необходимых полей в результате
REQUIRED_FIELDS=("document_type" "sections" "key_elements")
for field in "${REQUIRED_FIELDS[@]}"; do
    if ! echo "$ANALYSIS_RESULT" | jq --arg field "$field" 'has($field)' | grep -q true; then
        echo "Ошибка: В результате отсутствует обязательное поле '$field'" >&2
        exit 1
    fi
done

# Вывод результата
echo "$ANALYSIS_RESULT"
