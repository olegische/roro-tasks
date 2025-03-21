from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum

class DocumentType(str, Enum):
    INVOICE = "invoice"
    WAYBILL = "waybill"
    UPD = "upd"

class BoundingBox(BaseModel):
    x1: float = Field(..., description="Левая координата X")
    y1: float = Field(..., description="Верхняя координата Y")
    x2: float = Field(..., description="Правая координата X")
    y2: float = Field(..., description="Нижняя координата Y")

class DocumentSection(BaseModel):
    name: str = Field(..., description="Название раздела документа")
    bbox: BoundingBox = Field(..., description="Координаты расположения раздела")

class KeyElement(BaseModel):
    name: str = Field(..., description="Название элемента")
    value: str = Field(..., description="Значение элемента")
    bbox: BoundingBox = Field(..., description="Координаты расположения элемента")

class DocumentAnalysis(BaseModel):
    document_type: DocumentType = Field(..., description="Тип документа")
    sections: List[DocumentSection] = Field(default_factory=list, description="Разделы документа")
    key_elements: List[KeyElement] = Field(default_factory=list, description="Ключевые элементы")

class ExtractionArea(BaseModel):
    delta_x1: float = Field(..., description="Смещение по X от левого края")
    delta_y1: float = Field(..., description="Смещение по Y от верхнего края")
    delta_x2: float = Field(..., description="Смещение по X от правого края")
    delta_y2: float = Field(..., description="Смещение по Y от нижнего края")

class Anchor(BaseModel):
    text: str = Field(..., description="Текст якоря")
    text_threshold: float = Field(..., ge=0, le=1, description="Порог совпадения текста")
    repetition_index: int = Field(default=0, description="Индекс повторения")
    multiline: bool = Field(default=False, description="Многострочный текст")
    relation: str = Field(..., description="Тип отношения (main/top/right/bottom/left)")

class DSLTemplate(BaseModel):
    intersection_metric: Dict[str, Any] = Field(..., description="Метрика пересечения")
    extraction_area: ExtractionArea = Field(..., description="Область извлечения")
    type: str = Field(default="ChainAttribute", description="Тип атрибута")
    params: Dict[str, Any] = Field(..., description="Параметры шаблона")

class DocumentRequest(BaseModel):
    file_path: str = Field(..., description="Путь к файлу документа")
    query: str = Field(..., description="Запрос пользователя")

class DocumentResponse(BaseModel):
    analysis: DocumentAnalysis = Field(..., description="Результат анализа документа")
    dsl_template: DSLTemplate = Field(..., description="Сгенерированный DSL шаблон")
