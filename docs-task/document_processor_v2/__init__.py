"""
Document Processor V2
-------------------
Улучшенная версия процессора документов с использованием OpenAI Assistant API.

Основные компоненты:
- AssistantManager: Управление ассистентами OpenAI
- DocumentProcessor: Обработка документов и генерация шаблонов
"""

from .src.assistant_manager import AssistantManager
from .src.document_processor import DocumentProcessor

__all__ = ['AssistantManager', 'DocumentProcessor']
