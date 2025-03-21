#!/usr/bin/env python3

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
import openai
from openai import OpenAI

# Настройка логирования
logging.basicConfig(
    format='[%(asctime)s] %(levelname)s: %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class AssistantManager:
    """Менеджер для управления ассистентами OpenAI"""
    
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("Не установлена переменная окружения OPENAI_API_KEY")
        
        self.client = OpenAI()
        self.script_dir = Path(__file__).parent.parent
        self.assistants: Dict[str, str] = {}
        self.cache_dir = self.script_dir / 'cache'
        self.cache_dir.mkdir(exist_ok=True)

    def load_prompt(self, prompt_path: str) -> str:
        """Загрузка промпта из файла"""
        try:
            with open(self.script_dir / prompt_path) as f:
                return f.read()
        except FileNotFoundError as e:
            logger.error(f"Не удалось загрузить промпт {prompt_path}: {e}")
            raise

    def get_or_create_assistant(self, name: str, model: str, prompt_path: str, tools: List[Dict[str, Any]]) -> str:
        """Получение или создание ассистента с заданными параметрами"""
        if name in self.assistants:
            return self.assistants[name]

        try:
            instructions = self.load_prompt(prompt_path)
            assistant = self.client.beta.assistants.create(
                name=name,
                model=model,
                instructions=instructions,
                tools=tools
            )
            self.assistants[name] = assistant.id
            return assistant.id
        except Exception as e:
            logger.error(f"Ошибка при создании ассистента {name}: {e}")
            raise

    def create_thread(self) -> str:
        """Создание нового треда"""
        try:
            thread = self.client.beta.threads.create()
            return thread.id
        except Exception as e:
            logger.error(f"Ошибка при создании треда: {e}")
            raise

    def upload_file(self, file_path: str) -> str:
        """Загрузка файла для использования ассистентом"""
        try:
            with open(file_path, 'rb') as f:
                file = self.client.files.create(
                    file=f,
                    purpose='assistants'
                )
            return file.id
        except Exception as e:
            logger.error(f"Ошибка при загрузке файла {file_path}: {e}")
            raise

    def add_message(self, thread_id: str, content: str, file_id: Optional[str] = None) -> str:
        """Добавление сообщения в тред"""
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
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения: {e}")
            raise

    def run_assistant(self, thread_id: str, assistant_id: str) -> str:
        """Запуск ассистента"""
        try:
            run = self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=assistant_id
            )
            return run.id
        except Exception as e:
            logger.error(f"Ошибка при запуске ассистента: {e}")
            raise

    def wait_for_completion(self, thread_id: str, run_id: str, max_retries: int = 3) -> None:
        """Ожидание завершения выполнения с механизмом повторных попыток"""
        import time
        retries = 0
        
        while retries < max_retries:
            try:
                while True:
                    run = self.client.beta.threads.runs.retrieve(
                        thread_id=thread_id,
                        run_id=run_id
                    )
                    if run.status == "completed":
                        return
                    elif run.status in ["failed", "cancelled", "expired"]:
                        raise RuntimeError(f"Выполнение завершилось с ошибкой: {run.status}")
                    time.sleep(1)
            except Exception as e:
                retries += 1
                if retries >= max_retries:
                    raise
                logger.warning(f"Попытка {retries} из {max_retries} не удалась: {e}")
                time.sleep(2 ** retries)  # Экспоненциальная задержка

    def get_result(self, thread_id: str) -> str:
        """Получение результата выполнения"""
        try:
            messages = self.client.beta.threads.messages.list(
                thread_id=thread_id,
                order="desc",
                limit=1
            )
            return messages.data[0].content[0].text.value
        except Exception as e:
            logger.error(f"Ошибка при получении результата: {e}")
            raise

    def cleanup(self, file_id: str) -> None:
        """Очистка временных файлов"""
        try:
            self.client.files.delete(file_id)
        except Exception as e:
            logger.warning(f"Ошибка при удалении файла {file_id}: {e}")

    def get_cached_markup(self, image_path: str) -> Optional[Dict[str, Any]]:
        """Получение кэшированной разметки для изображения"""
        cache_file = self.cache_dir / f"{Path(image_path).stem}_markup.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Ошибка при чтении кэша {cache_file}: {e}")
        return None

    def cache_markup(self, image_path: str, markup: Dict[str, Any]) -> None:
        """Сохранение разметки в кэш"""
        cache_file = self.cache_dir / f"{Path(image_path).stem}_markup.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(markup, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Ошибка при сохранении в кэш {cache_file}: {e}")
