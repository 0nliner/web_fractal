"""Рендер :class:`DiagramModel` в разные форматы: Mermaid (по умолчанию,
универсально), fractal_cad JSON (модель редактора), сырой JSON.
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import asdict

from .model import DiagramModel

# ---------------------------------------------------------------------------
# Mermaid
# ---------------------------------------------------------------------------

def _base_type(text: str | None) -> str:
    """Тип → безопасный односложный токен для Mermaid (String(36)→String, str|None→str)."""
    if not text:
        return "any"
    t = text.split("|")[0].split("(")[0].split("[")[0].strip()
    t = re.sub(r"[^A-Za-z0-9_]", "", t) or "any"
    return t


def _mm_ident(name: str) -> str:
    """Идентификатор сущности/класса для Mermaid (без спецсимволов)."""
    return re.sub(r"[^A-Za-z0-9_]", "_", name) or "_"


def to_mermaid(model: DiagramModel, kind: str = "both") -> str:
    blocks: list[str] = []
    if kind in ("er", "both") and model.entities:
        blocks.append(_mermaid_er(model))
    if kind in ("class", "both") and model.classes:
        blocks.append(_mermaid_class(model))
    return "\n\n".join(blocks) if blocks else "%% пусто: ни таблиц, ни классов не найдено\n"


def _mermaid_er(model: DiagramModel) -> str:
    lines = ["erDiagram"]
    for ent in model.entities:
        lines.append(f"    {_mm_ident(ent.table)} {{")
        for f in ent.fields:
            key = "PK" if f.primary_key else ("FK" if f.fk_target else "")
            lines.append(f"        {_base_type(f.db_type or f.type)} {_mm_ident(f.name)} {key}".rstrip())
        lines.append("    }")
    tables = {e.table for e in model.entities}
    for r in model.relations:
        if r.src_table in tables and r.dst_table in tables:
            # FK: много «src» на одну «dst».
            lines.append(f'    {_mm_ident(r.src_table)} }}o--|| {_mm_ident(r.dst_table)} : {_mm_ident(r.src_field)}')
    return "\n".join(lines)


_VIS = {"public": "+", "protected": "#", "private": "-"}


def _mermaid_class(model: DiagramModel) -> str:
    lines = ["classDiagram"]
    known = {c.name for c in model.classes}
    for c in model.classes:
        lines.append(f"    class {_mm_ident(c.name)} {{")
        if c.is_abstract:
            lines.append("        <<abstract>>")
        for a in c.attributes:
            lines.append(f"        {_base_type(a.type)} {_mm_ident(a.name)}")
        for m in c.methods:
            ret = f" {_base_type(m.returns)}" if m.returns else ""
            args = ", ".join(_mm_ident(a.replace('*', '')) for a in m.args)
            lines.append(f"        {_VIS.get(m.visibility, '+')}{_mm_ident(m.name)}({args}){ret}")
        lines.append("    }")
    for c in model.classes:
        for b in c.bases:
            base = b.split("[")[0].strip()  # Generic[T] → Generic
            if base in known:
                lines.append(f"    {_mm_ident(base)} <|-- {_mm_ident(c.name)}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# fractal_cad JSON (модель ext_gefest_*: schemas → tables/fields/relations/types,
# objects/methods/variables/inheritance). id детерминированные — стабильный re-import/diff.
# ---------------------------------------------------------------------------

def _grid(i: int, total: int, dx: int = 320, dy: int = 240) -> dict:
    cols = max(1, math.ceil(math.sqrt(total)))
    return {"x": (i % cols) * dx, "y": (i // cols) * dy}


def to_cad(model: DiagramModel) -> dict:
    # ---- ERD ----
    type_ids: dict[str, str] = {}
    types: list[dict] = []
    for ent in model.entities:
        for f in ent.fields:
            key = f.db_type or f.type or "any"
            if key not in type_ids:
                tid = f"ty:{_base_type(key)}:{len(types)}"
                type_ids[key] = tid
                types.append({"id": tid, "type_name": _base_type(key), "db_type_name": key})

    tables, fields = [], []
    field_id = lambda tbl, fld: f"f:{tbl}.{fld}"
    n_tables = len(model.entities)
    for i, ent in enumerate(model.entities):
        tid = f"t:{ent.table}"
        tables.append({"id": tid, "name": ent.table, "frontend_metadata": _grid(i, n_tables)})
        for f in ent.fields:
            fields.append({
                "id": field_id(ent.table, f.name),
                "table_id": tid,
                "name": f.name,
                "is_primary_key": f.primary_key,
                "type_id": type_ids.get(f.db_type or f.type),
            })
    field_index = {fl["id"] for fl in fields}
    relations = []
    for r in model.relations:
        left, right = field_id(r.src_table, r.src_field), field_id(r.dst_table, r.dst_field)
        if left in field_index and right in field_index:
            relations.append({"left_field_id": left, "right_field_id": right})

    # ---- Class ----
    known = {c.name for c in model.classes}
    objects, methods, variables, inherits = [], [], [], []
    n_cls = len(model.classes)
    for i, c in enumerate(model.classes):
        oid = f"o:{c.name}"
        objects.append({
            "id": oid,
            "name": c.name,
            "obj_type": "interface" if c.is_abstract else "class",
            "frontend_metadata": _grid(i, n_cls),
        })
        for m in c.methods:
            methods.append({
                "id": f"m:{c.name}.{m.name}",
                "owner_id": oid,
                "name": m.name,
                "args": m.args,
                "result_type": m.returns,
                "is_async": m.is_async,
                "visibility": m.visibility,
            })
        for a in c.attributes:
            variables.append({"id": f"v:{c.name}.{a.name}", "owner_id": oid, "name": a.name, "type": a.type})
        for b in c.bases:
            base = b.split("[")[0].strip()
            if base in known:
                inherits.append({"parent_id": f"o:{base}", "child_id": oid})

    return {
        "erd_schema": {"types": types, "tables": tables, "fields": fields, "relations": relations},
        "class_schema": {"objects": objects, "methods": methods, "variables": variables, "inherits": inherits},
    }


def to_json(model: DiagramModel) -> dict:
    """Сырой промежуточный дамп модели (для отладки / кастомных потребителей)."""
    return {
        "entities": [asdict(e) for e in model.entities],
        "relations": [asdict(r) for r in model.relations],
        "classes": [asdict(c) for c in model.classes],
    }


def render(model: DiagramModel, fmt: str, kind: str) -> str:
    if fmt == "mermaid":
        return to_mermaid(model, kind)
    if fmt == "cad":
        return json.dumps(to_cad(model), ensure_ascii=False, indent=2)
    if fmt == "json":
        return json.dumps(to_json(model), ensure_ascii=False, indent=2)
    raise ValueError(f"unknown format: {fmt}")
