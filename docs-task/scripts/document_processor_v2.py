#!/usr/bin/env python3

import os
import json
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from .assistant_manager import AssistantManager

logging.basicConfig(
    format='[%(asctime)s] %(levelname)s: %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Процессор документов с использованием OpenAI Assistant API"""

    def __init__(self):
        self.assistant_manager = AssistantManager()
        self.markup_assistant_id = None
        self.template_assistant_id = None
        self.initialize_assistants()

    def initialize_assistants(self) -> None:
        """Инициализация ассистентов при первом использовании"""
        try:
            # Ассистент для разметки с GPT-4 Vision
            self.markup_assistant_id = self.assistant_manager.get_or_create_assistant(
                name="Document Markup Generator",
                model="gpt-4-vision-preview",
                prompt_path="instructions/markup_generator.prompt",
                tools=[{"type": "code_interpreter"}]
            )

            # Ассистент для генерации шаблонов
            self.template_assistant_id = self.assistant_manager.get_or_create_assistant(
                name="DSL Template Generator",
                model="gpt-4-turbo-preview",
                prompt_path="instructions/template_generator.prompt",
                tools=[{"type": "code_interpreter"}]
            )
        except Exception as e:
            logger.error(f"Ошибка при инициализации ассистентов: {e}")
            raise

    def generate_markup(self, image_path: str) -> Dict[str, Any]:
        """Генерация JSON разметки для изображения с использованием кэша"""
        logger.info(f"Генерация разметки для {image_path}")

        # Проверяем кэш
        cached_markup = self.assistant_manager.get_cached_markup(image_path)
        if cached_markup:
            logger.info(f"Найдена кэшированная разметка для {image_path}")
            return cached_markup

        # Если нет в кэше, генерируем новую разметку
        thread_id = self.assistant_manager.create_thread()
        file_id = self.assistant_manager.upload_file(image_path)

        try:
            # Отправляем изображение на анализ
            self.assistant_manager.add_message(
                thread_id,
                "Проанализируй изображение и создай JSON разметку с координатами всех текстовых элементов",
                file_id
            )

            # Запускаем обработку
            run_id = self.assistant_manager.run_assistant(thread_id, self.markup_assistant_id)
            self.assistant_manager.wait_for_completion(thread_id, run_id)

            # Получаем и парсим результат
            result = self.assistant_manager.get_result(thread_id)
            markup = json.loads(result)

            # Сохраняем в кэш
            self.assistant_manager.cache_markup(image_path, markup)
            return markup

        finally:
            self.assistant_manager.cleanup(file_id)

    def generate_template(self, markup: Dict[str, Any], query: str) -> str:
        """Генерация YAML шаблона на основе разметки и запроса пользователя"""
        logger.info(f"Генерация шаблона для запроса: {query}")
        
        thread_id = self.assistant_manager.create_thread()

        try:
            # Отправляем разметку и запрос пользователя
            message = (
                f"На основе запроса пользователя '{query}' и следующей разметки создай YAML шаблон "
                f"для извлечения нужных данных:\n\n{json.dumps(markup, indent=2, ensure_ascii=False)}"
            )
            self.assistant_manager.add_message(thread_id, message)

            # Запускаем обработку
            run_id = self.assistant_manager.run_assistant(thread_id, self.template_assistant_id)
            self.assistant_manager.wait_for_completion(thread_id, run_id)

            # Получаем результат
            result = self.assistant_manager.get_result(thread_id)
            
            # Извлекаем YAML из результата
            yaml_start = result.find('```yaml')
            yaml_end = result.find('```', yaml_start + 7)
            if yaml_start != -1 and yaml_end != -1:
                yaml_content = result[yaml_start + 7:yaml_end].strip()
            else:
                yaml_content = result

            # Проверяем валидность YAML
            try:
                yaml.safe_load(yaml_content)
            except yaml.YAMLError as e:
                logger.error(f"Сгенерированный YAML невалиден: {e}")
                raise

            return yaml_content

        except Exception as e:
            logger.error(f"Ошибка при генерации шаблона: {e}")
            raise

    def process_document(self, image_path: str, query: str, output_dir: Optional[str] = None) -> Dict[str, str]:
        """Полный процесс обработки документа"""
        try:
            # Определяем директорию для сохранения результатов
            output_dir = Path(output_dir) if output_dir else Path(image_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)

            # Генерация разметки
            markup = self.generate_markup(image_path)
            markup_path = output_dir / f"{Path(image_path).stem}.json"
            with open(markup_path, 'w', encoding='utf-8') as f:
                json.dump(markup, f, ensure_ascii=False, indent=2)
            logger.info(f"Разметка сохранена в {markup_path}")

            # Генерация шаблона
            template = self.generate_template(markup, query)
            
            # Формируем имя файла на основе запроса
            template_name = query.lower().replace(" ", "_").replace('"', '').replace("'", "")
            template_path = output_dir / f"{template_name}.yml"
            with open(template_path, 'w', encoding='utf-8') as f:
                f.write(template)
            logger.info(f"Шаблон сохранен в {template_path}")

            return {
                "markup_path": str(markup_path),
                "template_path": str(template_path)
            }

        except Exception as e:
            logger.error(f"Ошибка при обработке документа: {e}")
            raise

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Обработка документов и генерация DSL шаблонов')
    parser.add_argument('image_path', help='Путь к изображению документа')
    parser.add_argument('query', help='Запрос пользователя (например, "найди ИНН")')
    parser.add_argument('--output-dir', help='Директория для сохранения результатов', default=None)
    
    args = parser.parse_args()

    try:
        processor = DocumentProcessor()
        result = processor.process_document(args.image_path, args.query, args.output_dir)
        print(f"Обработка завершена успешно:")
        print(f"Разметка: {result['markup_path']}")
        print(f"Шаблон: {result['template_path']}")
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        import sys
        sys.exit(1)

if __name__ == '__main__':
    main()
