"""Промежуточная модель диаграмм — то, что извлекается из кода и во что потом
рендерятся эмиттеры (mermaid / fractal_cad JSON). Не зависит ни от SQLAlchemy,
ни от рантайма проекта: это просто данные.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Field:
    """Колонка ER-сущности (таблицы)."""
    name: str
    type: str                       # текст типа из Mapped[...] / mapped_column, напр. "str", "int | None"
    db_type: str | None = None      # SQLA-тип, если распознан явно (String(36), Integer, JSON …)
    primary_key: bool = False
    nullable: bool = False
    fk_target: str | None = None    # "table.column", если колонка — внешний ключ


@dataclass
class Entity:
    """ER-сущность = замапленный класс (есть __tablename__)."""
    cls: str                        # имя класса (UserModel)
    table: str                      # __tablename__ (users)
    module: str
    fields: list[Field] = field(default_factory=list)


@dataclass
class Relation:
    """Связь по внешнему ключу: src_table.src_field → dst_table.dst_field."""
    src_table: str
    src_field: str
    dst_table: str
    dst_field: str


@dataclass
class Method:
    name: str
    args: list[str] = field(default_factory=list)   # без self/cls
    returns: str | None = None
    is_async: bool = False
    visibility: str = "public"      # public | protected | private


@dataclass
class Attribute:
    name: str
    type: str | None = None


@dataclass
class ClassInfo:
    """Узел классовой диаграммы — любой class в коде."""
    name: str
    module: str
    bases: list[str] = field(default_factory=list)      # базовые классы (наследование)
    methods: list[Method] = field(default_factory=list)
    attributes: list[Attribute] = field(default_factory=list)
    is_abstract: bool = False       # ABC / abstractmethod внутри


@dataclass
class DiagramModel:
    """Полный результат разбора: ER (entities+relations) + классы."""
    entities: list[Entity] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not (self.entities or self.classes)
