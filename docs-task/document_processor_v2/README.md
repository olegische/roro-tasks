# Document Processor V2

Улучшенная версия процессора документов с использованием OpenAI Assistant API.

## Особенности

- Использование специализированных ассистентов для разных задач
- Кэширование разметки для оптимизации
- Переиспользование ассистентов
- Улучшенная обработка ошибок
- Поддержка асинхронных операций

## Структура

```
document_processor_v2/
├── prompts/                  # Промпты для ассистентов
│   ├── markup_generator.prompt
│   └── template_generator.prompt
├── src/                     # Исходный код
│   ├── assistant_manager.py # Управление ассистентами
│   └── document_processor.py # Основной процессор
├── cache/                   # Кэш разметки (создается автоматически)
├── __init__.py             # Инициализация пакета
└── requirements.txt        # Зависимости
```

## Установка

```bash
pip install -r requirements.txt
```

## Использование

```python
from document_processor_v2 import DocumentProcessor

# Создание процессора
processor = DocumentProcessor()

# Обработка документа
result = processor.process_document(
    image_path="path/to/document.jpg",
    query="найди ИНН продавца",
    output_dir="path/to/output"
)

print(f"Разметка: {result['markup_path']}")
print(f"Шаблон: {result['template_path']}")
```

## Требования

- Python 3.8+
- OpenAI API ключ (установите в переменную окружения OPENAI_API_KEY)
- Доступ к GPT-4 Vision API
