#!/usr/bin/env python3

import os
import sys
import time
import json
import logging
import argparse
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

class DocumentAssistant:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("Не установлена переменная окружения OPENAI_API_KEY")
        
        self.client = OpenAI()
        self.script_dir = Path(__file__).parent

    def load_prompts(self) -> tuple[str, str]:
        """Загрузка промптов из файлов"""
        try:
            with open(self.script_dir / '../prompts/document_analyzer.prompt') as f:
                document_analyzer_prompt = f.read()
            
            with open(self.script_dir / '../prompts/dsl_generator.prompt') as f:
                dsl_generator_prompt = f.read()
            
            return document_analyzer_prompt, dsl_generator_prompt
        except FileNotFoundError as e:
            logger.error(f"Не удалось загрузить промпты: {e}")
            raise

    def create_assistant(self) -> str:
        """Создание ассистента"""
        logger.info("Создание ассистента...")
        
        document_analyzer_prompt, dsl_generator_prompt = self.load_prompts()
        
        instructions = f"""
        Ты - эксперт по анализу документов и созданию DSL шаблонов. Твоя задача:

        1. Анализ документа:
        {document_analyzer_prompt}

        2. Генерация DSL:
        {dsl_generator_prompt}

        Используй code_interpreter для обработки изображений и создания точных координат.
        """

        try:
            assistant = self.client.beta.assistants.create(
                name="Document DSL Generator",
                description="Анализирует документы и создает DSL шаблоны для извлечения данных",
                model="gpt-4-vision-preview",
                instructions=instructions,
                tools=[{"type": "code_interpreter"}]
            )
            return assistant.id
        except openai.OpenAIError as e:
            logger.error(f"Ошибка при создании ассистента: {e}")
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

    def process_document(self, document_path: str, user_query: str) -> str:
        """Основной процесс обработки документа"""
        try:
            # 1. Создание ассистента
            assistant_id = self.create_assistant()

            # 2. Создание треда
            thread_id = self.create_thread()

            # 3. Загрузка документа
            file_id = self.upload_file(document_path)

            try:
                # 4. Добавление сообщения
                self.add_message(thread_id, user_query, file_id)

                # 5. Запуск ассистента
                run_id = self.run_assistant(thread_id, assistant_id)

                # 6. Ожидание завершения
                self.wait_for_completion(thread_id, run_id)

                # 7. Получение результата
                result = self.get_result(thread_id)

                return result
            finally:
                # 8. Очистка
                self.cleanup(file_id)

        except Exception as e:
            logger.error(f"Ошибка при обработке документа: {e}")
            raise

def main():
    parser = argparse.ArgumentParser(description='Анализ документов и создание DSL шаблонов')
    parser.add_argument('document_path', help='Путь к документу')
    parser.add_argument('user_query', help='Запрос пользователя')
    
    args = parser.parse_args()

    try:
        assistant = DocumentAssistant()
        result = assistant.process_document(args.document_path, args.user_query)
        print(result)
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
