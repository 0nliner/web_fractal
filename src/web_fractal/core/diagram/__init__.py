"""Реверс-инжиниринг ER и классовых диаграмм из существующего кода.

Публичный API (вызывается и из ``wf diagram``, и как библиотечный метод):

    from web_fractal.core.diagram import build_diagrams, render
    model = build_diagrams("app")            # статический разбор пакета/файла/модуля
    print(render(model, fmt="mermaid", kind="both"))
"""
from __future__ import annotations

from .emit import render, to_cad, to_json, to_mermaid
from .extractor import build_diagrams
from .model import (
    Attribute,
    ClassInfo,
    DiagramModel,
    Entity,
    Field,
    Method,
    Relation,
)

__all__ = [
    "build_diagrams",
    "render",
    "to_mermaid",
    "to_cad",
    "to_json",
    "DiagramModel",
    "Entity",
    "Field",
    "Relation",
    "ClassInfo",
    "Method",
    "Attribute",
]
