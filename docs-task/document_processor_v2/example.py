#!/usr/bin/env python3

import os
from pathlib import Path
from document_processor_v2 import DocumentProcessor

def main():
    """
    Пример использования Document Processor V2
    """
    # Проверяем наличие API ключа
    if not os.getenv('OPENAI_API_KEY'):
        print("Ошибка: Не установлена переменная окружения OPENAI_API_KEY")
        return

    try:
        # Создаем процессор
        processor = DocumentProcessor()

        # Путь к тестовому изображению
        image_path = "Примеры-для-AI-Agent/Счет-Фактура/Примеры документов/20.jpg"

        # Запросы для обработки
        queries = [
            "найди ИНН продавца",
            "найди дату",
            "найди номер документа"
        ]

        # Обрабатываем каждый запрос
        for query in queries:
            print(f"\nОбработка запроса: {query}")
            
            result = processor.process_document(
                image_path=image_path,
                query=query,
                output_dir="results"
            )
            
            print(f"Результаты:")
            print(f"  Разметка: {result['markup_path']}")
            print(f"  Шаблон: {result['template_path']}")

    except Exception as e:
        print(f"Ошибка при обработке: {e}")

if __name__ == '__main__':
    main()
