#!/bin/bash

# Проверка наличия API ключа
if [ -z "$OPENAI_API_KEY" ]; then
    echo "Ошибка: Не установлена переменная окружения OPENAI_API_KEY" >&2
    exit 1
fi

# Проверка аргументов
if [ "$#" -ne 1 ]; then
    echo "Использование: $0 path/to/document.jpg" >&2
    exit 1
fi

DOCUMENT_PATH="$1"

# Проверка существования файла
if [ ! -f "$DOCUMENT_PATH" ]; then
    echo "Ошибка: Файл $DOCUMENT_PATH не существует" >&2
    exit 1
fi

# Проверка типа файла
FILE_TYPE=$(file -b --mime-type "$DOCUMENT_PATH")
case "$FILE_TYPE" in
    image/jpeg|image/png|image/tiff|application/pdf)
        # Поддерживаемые типы файлов
        ;;
    *)
        echo "Ошибка: Неподдерживаемый тип файла $FILE_TYPE. Поддерживаются только JPEG, PNG, TIFF и PDF" >&2
        exit 1
        ;;
esac

# Получение размера файла
FILE_SIZE=$(stat -f%z "$DOCUMENT_PATH")
if [ "$FILE_SIZE" -gt 524288000 ]; then # 500MB в байтах
    echo "Ошибка: Размер файла превышает 500MB" >&2
    exit 1
fi

# Загрузка файла
RESPONSE=$(curl -s -X POST "https://api.openai.com/v1/files" \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -H "OpenAI-Beta: assistants=v2" \
    -F "purpose=assistants" \
    -F "file=@$DOCUMENT_PATH")

# Проверка ответа
if echo "$RESPONSE" | jq -e '.error' >/dev/null; then
    ERROR_MSG=$(echo "$RESPONSE" | jq -r '.error.message')
    echo "Ошибка при загрузке файла: $ERROR_MSG" >&2
    exit 1
fi

# Проверка наличия ID файла в ответе
if ! echo "$RESPONSE" | jq -e '.id' >/dev/null; then
    echo "Ошибка: Не удалось получить ID файла из ответа API" >&2
    exit 1
fi

# Вывод результата
echo "$RESPONSE"
