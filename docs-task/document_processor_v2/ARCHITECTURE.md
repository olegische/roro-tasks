# Архитектура Document Processor V2

## Общая структура

```mermaid
graph TB
    Client --> DP["DocumentProcessor"]
    
    subgraph "Document Processor V2"
        DP --> AM["AssistantManager"]
        DP --> AM
        
        subgraph "Assistant Manager"
            AM --> Assistants["Assistant Pool"]
            AM --> Cache["Markup Cache"]
            AM --> Files["Files"]
            AM --> Threads["Threads"]
        end
    end
    
    Assistants --> MA["Markup Assistant\nGPT-4 Vision"]
    Assistants --> TA["Template Assistant\nGPT-4 Turbo"]
    
    MA --> Image["Image Analysis"]
    TA --> DSL["YAML DSL Generation"]
```

## Взаимодействие с OpenAI Assistant API

```mermaid
sequenceDiagram
    participant AM as AssistantManager
    participant API as OpenAI API
    participant AS as Assistant
    participant TH as Thread
    participant FL as Files

    Note over AM,API: Assistant Initialization
    AM->>API: Create Assistant
    API-->>AM: assistant_id
    
    Note over AM,API: File Upload
    AM->>API: Upload File
    API-->>AM: file_id
    
    Note over AM,API: Thread Creation
    AM->>API: Create Thread
    API-->>AM: thread_id
    
    Note over AM,API: Message Sending
    AM->>API: Add Message to Thread
    API-->>AM: message_id
    
    Note over AM,API: Start Processing
    AM->>API: Create Run
    API-->>AM: run_id
    
    loop Check Status
        AM->>API: Get Run Status
        API-->>AM: status
        alt status == completed
            API-->>AM: Result
        else status == failed
            API-->>AM: Error
        end
    end
```

## Процесс обработки документа

```mermaid
sequenceDiagram
    participant C as Client
    participant DP as DocumentProcessor
    participant AM as AssistantManager
    participant MA as Markup Assistant
    participant TA as Template Assistant
    participant Cache as Markup Cache

    C->>DP: process_document(image, query)
    
    DP->>AM: generate_markup(image)
    AM->>Cache: get_cached_markup(image)
    
    alt Cache Hit
        Cache-->>AM: cached_markup
        AM-->>DP: cached_markup
    else Cache Miss
        AM->>MA: create_thread()
        AM->>MA: upload_file(image)
        MA-->>AM: file_id
        AM->>MA: add_message(analyze)
        MA-->>AM: markup
        AM->>Cache: cache_markup(markup)
        AM-->>DP: markup
    end
    
    DP->>AM: generate_template(markup, query)
    AM->>TA: create_thread()
    AM->>TA: add_message(generate)
    TA-->>AM: yaml_template
    AM-->>DP: yaml_template
    
    DP-->>C: {markup_path, template_path}
```

## Компоненты системы

```mermaid
classDiagram
    class DocumentProcessor {
        -AssistantManager assistant_manager
        -str markup_assistant_id
        -str template_assistant_id
        +__init__()
        +initialize_assistants()
        +generate_markup(image_path)
        +generate_template(markup, query)
        +process_document(image_path, query)
    }
    
    class AssistantManager {
        -OpenAI client
        -dict assistants
        -Path cache_dir
        +__init__()
        +load_prompt(prompt_path)
        +get_or_create_assistant(name, model, prompt)
        +create_thread()
        +upload_file(file_path)
        +add_message(thread_id, content)
        +run_assistant(thread_id, assistant_id)
        +wait_for_completion(thread_id, run_id)
        +get_result(thread_id)
        +cleanup(file_id)
        +get_cached_markup(image_path)
        +cache_markup(image_path, markup)
    }
    
    DocumentProcessor --> AssistantManager
```

## Особенности реализации

### 1. Управление ассистентами
```mermaid
graph LR
    subgraph "AssistantManager"
        Init[Initialization] -->|"Create/Get"| Pool[Assistant Pool]
        Pool -->|"Store ID"| Cache[Assistant Cache]
        Pool --> MA[Markup Assistant]
        Pool --> TA[Template Assistant]
    end
    
    MA -->|"GPT-4 Vision"| Vision[Image Analysis]
    TA -->|"GPT-4 Turbo"| DSL[DSL Generation]
```

### 2. Кэширование разметки
```mermaid
graph TD
    subgraph "Caching"
        Check[Cache Check] -->|"Hit"| Get[Get Markup]
        Check -->|"Miss"| Gen[Generate New]
        Gen --> Save[Save to Cache]
        
        Save -->|"JSON"| FS[File System]
        Get -->|"JSON"| Use[Use]
    end
```

### 3. Обработка ошибок
```mermaid
graph TD
    subgraph "Retry Mechanism"
        Err[Error] --> Retry[Retry]
        Retry -->|"Success"| Success[Complete]
        Retry -->|"Error"| Check[Check Attempts]
        Check -->|"Attempts Left"| Retry
        Check -->|"No Attempts"| Fail[Execution Error]
    end
```

## Преимущества архитектуры

1. **Разделение ответственности**
   - DocumentProcessor: высокоуровневая логика
   - AssistantManager: управление ресурсами OpenAI
   - Специализированные ассистенты: конкретные задачи

2. **Оптимизация ресурсов**
   - Переиспользование ассистентов
   - Кэширование разметки
   - Эффективное управление файлами

3. **Надежность**
   - Механизм повторных попыток
   - Детальное логирование
   - Корректная очистка ресурсов

4. **Расширяемость**
   - Легкое добавление новых ассистентов
   - Гибкая настройка промптов
   - Модульная структура

## Особенности работы с Assistant API

1. **Переиспользование ассистентов**
   - Ассистенты создаются один раз при инициализации
   - ID ассистентов сохраняются в памяти
   - Повторное использование существующих ассистентов

2. **Управление тредами**
   - Каждый запрос создает новый тред
   - Треды изолируют контекст обработки
   - Автоматическая очистка после использования

3. **Работа с файлами**
   - Временная загрузка для анализа
   - Автоматическая очистка после использования
   - Поддержка различных форматов

4. **Промпты и инструкции**
   - Разделение промптов по задачам
   - Четкие инструкции для каждого ассистента
   - Возможность настройки под конкретные типы документов

5. **Обработка результатов**
   - Парсинг JSON разметки
   - Валидация YAML шаблонов
   - Сохранение в файловой системе
