# Document Analysis API

API для анализа документов и генерации DSL шаблонов с использованием OpenAI Assistant API.

## Описание

API предоставляет возможность:
- Анализировать документы (счета-фактуры, накладные, УПД)
- Определять структуру и ключевые элементы документов
- Генерировать DSL шаблоны для извлечения данных

## Установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd easydocs-task/api
```

2. Создайте виртуальное окружение и активируйте его:
```bash
python -m venv venv
source venv/bin/activate  # для Linux/Mac
# или
venv\Scripts\activate  # для Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл .env и добавьте API ключ OpenAI:
```bash
echo "OPENAI_API_KEY=your-api-key" > .env
```

## Запуск

Запустите сервер:
```bash
uvicorn main:app --reload
```

API будет доступно по адресу: http://localhost:8000

Документация Swagger UI: http://localhost:8000/docs

## API Endpoints

### POST /analyze

Анализ документа и генерация DSL шаблона.

**Параметры запроса:**
- `file`: Файл документа (изображение)
- `query`: Запрос пользователя (опционально)

**Пример запроса с использованием curl:**
```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@path/to/document.jpg" \
  -F "query=Найди ИНН покупателя"
```

**Пример ответа:**
```json
{
  "analysis": {
    "document_type": "invoice",
    "sections": [
      {
        "name": "Заголовок",
        "bbox": {
          "x1": 100,
          "y1": 50,
          "x2": 500,
          "y2": 150
        }
      }
    ],
    "key_elements": [
      {
        "name": "ИНН_Покупателя",
        "value": "7707083893",
        "bbox": {
          "x1": 200,
          "y1": 300,
          "x2": 300,
          "y2": 320
        }
      }
    ]
  },
  "dsl_template": {
    "intersection_metric": {
      "name": "Overlap",
      "threshold": 0.6
    },
    "extraction_area": {
      "delta_x1": 10,
      "delta_y1": 0,
      "delta_x2": 100,
      "delta_y2": 20
    },
    "type": "ChainAttribute",
    "params": {
      "attributes": [
        {
          "type": "AnchorsBasedAttribute",
          "priority": 1,
          "params": {
            "anchors": [
              {
                "text": "ИНН",
                "text_threshold": 0.8,
                "repetition_index": 0,
                "multiline": false,
                "relation": "right"
              }
            ]
          }
        }
      ]
    }
  }
}
```

## Модели данных

### DocumentType
Перечисление типов документов:
- `invoice` - Счет-фактура
- `waybill` - Накладная
- `upd` - УПД

### BoundingBox
Координаты области на изображении:
- `x1`: float - Левая координата X
- `y1`: float - Верхняя координата Y
- `x2`: float - Правая координата X
- `y2`: float - Нижняя координата Y

### DocumentSection
Раздел документа:
- `name`: string - Название раздела
- `bbox`: BoundingBox - Координаты расположения

### KeyElement
Ключевой элемент документа:
- `name`: string - Название элемента
- `value`: string - Значение элемента
- `bbox`: BoundingBox - Координаты расположения

### DocumentAnalysis
Результат анализа документа:
- `document_type`: DocumentType - Тип документа
- `sections`: List[DocumentSection] - Разделы документа
- `key_elements`: List[KeyElement] - Ключевые элементы

### DSLTemplate
Шаблон для извлечения данных:
- `intersection_metric`: Dict - Метрика пересечения
- `extraction_area`: ExtractionArea - Область извлечения
- `type`: string - Тип атрибута
- `params`: Dict - Параметры шаблона

## Обработка ошибок

API возвращает следующие коды ошибок:
- 400: Неверный запрос
- 422: Ошибка валидации
- 500: Внутренняя ошибка сервера

## Разработка

1. Установите дополнительные зависимости для разработки:
```bash
pip install black isort pytest
```

2. Запустите тесты:
```bash
pytest
```

3. Отформатируйте код:
```bash
black .
isort .
