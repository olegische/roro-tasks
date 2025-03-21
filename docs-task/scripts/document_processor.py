#!/usr/bin/env python3

import os
import json
import yaml
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import openai
from openai import OpenAI

# Настройка логирования
logging.basicConfig(
    format='[%(asctime)s] %(levelname)s: %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("Не установлена переменная окружения OPENAI_API_KEY")
        
        self.client = OpenAI()
        self.script_dir = Path(__file__).parent.parent

    def load_prompts(self) -> tuple[str, str]:
        """Загрузка промптов"""
        try:
            with open(self.script_dir / 'instructions/markup_generator.prompt') as f:
                markup_prompt = f.read()
            
            with open(self.script_dir / 'instructions/template_generator.prompt') as f:
                template_prompt = f.read()
            
            return markup_prompt, template_prompt
        except FileNotFoundError as e:
            logger.error(f"Не удалось загрузить промпты: {e}")
            raise

    def create_markup_assistant(self, markup_prompt: str) -> str:
        """Создание ассистента для разметки"""
        logger.info("Создание ассистента для разметки...")
        try:
            assistant = self.client.beta.assistants.create(
                name="Document Markup Generator",
                description="Создает JSON разметку документов с координатами элементов",
                model="gpt-4-vision-preview",
                instructions=markup_prompt,
                tools=[{"type": "code_interpreter"}]
            )
            return assistant.id
        except openai.OpenAIError as e:
            logger.error(f"Ошибка при создании ассистента для разметки: {e}")
            raise

    def create_template_assistant(self, template_prompt: str) -> str:
        """Создание ассистента для генерации шаблонов"""
        logger.info("Создание ассистента для генерации шаблонов...")
        try:
            assistant = self.client.beta.assistants.create(
                name="DSL Template Generator",
                description="Создает YAML шаблоны на основе разметки",
                model="gpt-4-turbo-preview",
                instructions=template_prompt,
                tools=[{"type": "code_interpreter"}]
            )
            return assistant.id
        except openai.OpenAIError as e:
            logger.error(f"Ошибка при создании ассистента для шаблонов: {e}")
            raise

    def create_thread(self) -> str:
        """Создание треда"""
        logger.info("Создание треда...")
        try:
            thread = self.client.beta.threads.create()
            return thread.id
        except openai.OpenAIError as e:
            logger.error(f"Ошибка при создании треда: {e}")
            raise

    def upload_file(self, file_path: str) -> str:
        """Загрузка файла"""
        logger.info("Загрузка файла...")
        try:
            with open(file_path, 'rb') as f:
                file = self.client.files.create(
                    file=f,
                    purpose='assistants'
                )
            return file.id
        except (openai.OpenAIError, IOError) as e:
            logger.error(f"Ошибка при загрузке файла: {e}")
            raise

    def add_message(self, thread_id: str, content: str, file_id: Optional[str] = None) -> str:
        """Добавление сообщения в тред"""
        logger.info("Отправка сообщения...")
        try:
            message_params = {
                "role": "user",
                "content": content
            }
            
            if file_id:
                message_params["file_ids"] = [file_id]
            
            message = self.client.beta.threads.messages.create(
                thread_id=thread_id,
                **message_params
            )
            return message.id
        except openai.OpenAIError as e:
            logger.error(f"Ошибка при отправке сообщения: {e}")
            raise

    def run_assistant(self, thread_id: str, assistant_id: str) -> str:
        """Запуск выполнения"""
        logger.info("Запуск обработки...")
        try:
            run = self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=assistant_id
            )
            return run.id
        except openai.OpenAIError as e:
            logger.error(f"Ошибка при запуске ассистента: {e}")
            raise

    def wait_for_completion(self, thread_id: str, run_id: str) -> None:
        """Ожидание завершения выполнения"""
        logger.info("Ожидание результата...")
        while True:
            try:
                run = self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run_id
                )
                if run.status == "completed":
                    break
                elif run.status in ["failed", "cancelled", "expired"]:
                    raise RuntimeError(f"Выполнение завершилось с ошибкой: {run.status}")
                time.sleep(1)
            except openai.OpenAIError as e:
                logger.error(f"Ошибка при проверке статуса: {e}")
                raise

    def get_result(self, thread_id: str) -> str:
        """Получение результата"""
        logger.info("Получение результата...")
        try:
            messages = self.client.beta.threads.messages.list(
                thread_id=thread_id,
                order="desc",
                limit=1
            )
            return messages.data[0].content[0].text.value
        except openai.OpenAIError as e:
            logger.error(f"Ошибка при получении результата: {e}")
            raise

    def cleanup(self, file_id: str) -> None:
        """Очистка временных файлов"""
        logger.info("Удаление временных файлов...")
        try:
            self.client.files.delete(file_id)
        except openai.OpenAIError as e:
            logger.warning(f"Ошибка при удалении файла: {e}")

    def generate_markup(self, image_path: str) -> Dict[str, Any]:
        """Генерация JSON разметки для изображения"""
        logger.info(f"Генерация разметки для {image_path}")
        
        markup_prompt, _ = self.load_prompts()
        assistant_id = self.create_markup_assistant(markup_prompt)
        thread_id = self.create_thread()
        file_id = self.upload_file(image_path)

        try:
            # Отправляем изображение на анализ
            self.add_message(
                thread_id,
                "Проанализируй изображение и создай JSON разметку с координатами всех текстовых элементов",
                file_id
            )

            # Запускаем обработку
            run_id = self.run_assistant(thread_id, assistant_id)
            self.wait_for_completion(thread_id, run_id)

            # Получаем результат
            result = self.get_result(thread_id)
            return json.loads(result)

        finally:
            self.cleanup(file_id)

    def generate_template(self, markup: Dict[str, Any], query: str) -> str:
        """Генерация YAML шаблона на основе разметки и запроса пользователя"""
        logger.info(f"Генерация шаблона для запроса: {query}")
        
        _, template_prompt = self.load_prompts()
        assistant_id = self.create_template_assistant(template_prompt)
        thread_id = self.create_thread()

        try:
            # Отправляем разметку и запрос пользователя
            message = (
                f"На основе запроса пользователя '{query}' и следующей разметки создай YAML шаблон "
                f"для извлечения нужных данных:\n\n{json.dumps(markup, indent=2)}"
            )
            self.add_message(thread_id, message)

            # Запускаем обработку
            run_id = self.run_assistant(thread_id, assistant_id)
            self.wait_for_completion(thread_id, run_id)

            # Получаем результат
            result = self.get_result(thread_id)
            
            # Извлекаем YAML из результата
            yaml_start = result.find('```yaml')
            yaml_end = result.find('```', yaml_start + 7)
            if yaml_start != -1 and yaml_end != -1:
                yaml_content = result[yaml_start + 7:yaml_end].strip()
            else:
                yaml_content = result

            return yaml_content

        except Exception as e:
            logger.error(f"Ошибка при генерации шаблона: {e}")
            raise

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Обработка документов и генерация DSL шаблонов')
    parser.add_argument('image_path', help='Путь к изображению документа')
    parser.add_argument('query', help='Запрос пользователя (например, "найди ИНН")')
    parser.add_argument('--output-dir', help='Директория для сохранения результатов', default='.')
    
    args = parser.parse_args()

    try:
        processor = DocumentProcessor()

        # Генерация разметки
        markup = processor.generate_markup(args.image_path)
        markup_path = Path(args.output_dir) / f"{Path(args.image_path).stem}.json"
        with open(markup_path, 'w', encoding='utf-8') as f:
            json.dump(markup, f, ensure_ascii=False, indent=2)
        logger.info(f"Разметка сохранена в {markup_path}")

        # Генерация шаблона
        template = processor.generate_template(markup, args.query)
        
        # Формируем имя файла на основе запроса
        template_name = args.query.lower().replace(" ", "_").replace('"', '').replace("'", "")
        template_path = Path(args.output_dir) / f"{template_name}.yml"
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(template)
        logger.info(f"Шаблон сохранен в {template_path}")

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
