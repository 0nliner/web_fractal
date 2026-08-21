"""Статический разбор Python-кода в модель диаграмм (без импорта проекта).

ER: класс с ``__tablename__`` = таблица; колонки — ``name: Mapped[T] =
mapped_column(...)``; связи — из ``ForeignKey("table.col")``.
Классовая: любой class → имя, базы (наследование), методы, типизированные
атрибуты (в т.ч. DI-аннотации archtool ``service: FooServiceABC``).
"""
from __future__ import annotations

import ast
from pathlib import Path

from .model import Attribute, ClassInfo, DiagramModel, Entity, Field, Method, Relation

_SKIP_DIRS = {"__pycache__", ".git", ".venv", "venv", "node_modules", ".mypy_cache", ".pytest_cache"}


def build_diagrams(target: str | Path) -> DiagramModel:
    """Собирает :class:`DiagramModel` из файла, каталога или dotted-модуля."""
    root = _resolve(target)
    model = DiagramModel()
    # Реестры для разрешения наследования: колонки часто приходят из миксинов
    # (Dated, WithTimestamps) и абстрактных баз (BaseSchema) — их поля надо влить.
    own_fields: dict[str, list[Field]] = {}
    bases_of: dict[str, list[str]] = {}
    entity_specs: list[tuple[str, str, str]] = []  # (class_name, table, module)

    for path in _iter_py_files(root):
        try:
            _parse_file(path, root, model, own_fields, bases_of, entity_specs)
        except SyntaxError:
            # Битый/несовместимый файл не должен ронять весь прогон.
            continue

    # Поля сущностей = собственные + унаследованные (по всему разобранному коду).
    for cls_name, table, module in entity_specs:
        fields = _resolve_fields(cls_name, own_fields, bases_of)
        model.entities.append(Entity(cls=cls_name, table=table, module=module, fields=fields))

    # Связи строим по FK после сбора всех сущностей (порядок файлов не важен).
    for ent in model.entities:
        for f in ent.fields:
            if f.fk_target and "." in f.fk_target:
                dst_table, dst_field = f.fk_target.split(".", 1)
                model.relations.append(Relation(ent.table, f.name, dst_table, dst_field))
    return model


def _resolve_fields(
    cls_name: str,
    own_fields: dict[str, list[Field]],
    bases_of: dict[str, list[str]],
    seen: set[str] | None = None,
) -> list[Field]:
    """Поля класса: сначала из баз (рекурсивно), затем собственные (перекрывают по имени)."""
    seen = seen if seen is not None else set()
    if cls_name in seen:
        return []
    seen.add(cls_name)
    merged: dict[str, Field] = {}
    for base in bases_of.get(cls_name, []):
        base_name = base.split("[")[0].split(".")[-1].strip()  # module.Base[T] → Base
        for f in _resolve_fields(base_name, own_fields, bases_of, seen):
            merged[f.name] = f
    for f in own_fields.get(cls_name, []):
        merged[f.name] = f
    return list(merged.values())


# ---------------------------------------------------------------------------
# Target resolution
# ---------------------------------------------------------------------------

def _resolve(target: str | Path) -> Path:
    p = Path(target)
    if p.exists():
        return p
    # dotted-модуль: app.crm → app/crm
    dotted = Path(*str(target).split("."))
    if dotted.exists():
        return dotted
    if dotted.with_suffix(".py").exists():
        return dotted.with_suffix(".py")
    raise FileNotFoundError(f"target not found: {target}")


def _iter_py_files(root: Path):
    if root.is_file():
        if root.suffix == ".py":
            yield root
        return
    for path in sorted(root.rglob("*.py")):
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        yield path


def _module_name(path: Path, root: Path) -> str:
    base = root.parent if root.is_file() else root
    try:
        rel = path.relative_to(base)
    except ValueError:
        rel = path
    return str(rel.with_suffix("")).replace("/", ".").replace("\\", ".")


# ---------------------------------------------------------------------------
# Per-file parsing
# ---------------------------------------------------------------------------

def _parse_file(
    path: Path,
    root: Path,
    model: DiagramModel,
    own_fields: dict[str, list[Field]],
    bases_of: dict[str, list[str]],
    entity_specs: list[tuple[str, str, str]],
) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    module = _module_name(path, root)
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            _handle_class(node, module, model, own_fields, bases_of, entity_specs)


def _handle_class(
    node: ast.ClassDef,
    module: str,
    model: DiagramModel,
    own_fields: dict[str, list[Field]],
    bases_of: dict[str, list[str]],
    entity_specs: list[tuple[str, str, str]],
) -> None:
    # Собственные колонки и базы регистрируем для ЛЮБОГО класса — миксины/абстрактные
    # базы (без __tablename__) сами не сущности, но их поля наследуют таблицы.
    own_fields[node.name] = _fields(node)
    bases_of[node.name] = [_unparse(b) for b in node.bases]
    table = _tablename(node)
    if table is not None:
        entity_specs.append((node.name, table, module))
    model.classes.append(_class_info(node, module))


def _tablename(node: ast.ClassDef) -> str | None:
    for stmt in node.body:
        if isinstance(stmt, ast.Assign):
            for tgt in stmt.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "__tablename__":
                    if isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                        return stmt.value.value
    return None


# ---- ER fields ------------------------------------------------------------

def _fields(node: ast.ClassDef) -> list[Field]:
    out: list[Field] = []
    for stmt in node.body:
        if not isinstance(stmt, ast.AnnAssign) or not isinstance(stmt.target, ast.Name):
            continue
        name = stmt.target.id
        if name.startswith("__"):
            continue
        mapped_inner = _mapped_inner(stmt.annotation)
        if mapped_inner is None:
            continue  # не колонка (обычная аннотация — уйдёт в атрибуты класса)
        # relationship()/column_property()/прочие вызовы — ORM-навигация, не колонка
        # (сама связь берётся из ForeignKey). Колонка = mapped_column(...) или без value.
        if isinstance(stmt.value, ast.Call) and _call_name(stmt.value.func) != "mapped_column":
            continue
        type_text, ann_nullable = _clean_type(mapped_inner)
        f = Field(name=name, type=type_text, nullable=ann_nullable)
        if isinstance(stmt.value, ast.Call) and _call_name(stmt.value.func) == "mapped_column":
            _apply_mapped_column(stmt.value, f)
        out.append(f)
    return out


def _mapped_inner(annotation: ast.expr) -> ast.expr | None:
    """Из ``Mapped[T]`` достаёт ``T``; иначе None."""
    if isinstance(annotation, ast.Subscript) and _call_name(annotation.value) == "Mapped":
        return annotation.slice
    return None


def _apply_mapped_column(call: ast.Call, f: Field) -> None:
    for arg in call.args:
        if isinstance(arg, ast.Call):
            fn = _call_name(arg.func)
            if fn == "ForeignKey" and arg.args and isinstance(arg.args[0], ast.Constant):
                f.fk_target = str(arg.args[0].value)
            elif fn and f.db_type is None:  # String(36), Integer(), …
                f.db_type = _unparse(arg)
        elif isinstance(arg, ast.Name) and f.db_type is None:  # Integer, Text без вызова
            f.db_type = arg.id
    for kw in call.keywords:
        if kw.arg == "primary_key" and _is_true(kw.value):
            f.primary_key = True
        elif kw.arg == "nullable":
            f.nullable = _is_true(kw.value)


# ---- Class info -----------------------------------------------------------

def _class_info(node: ast.ClassDef, module: str) -> ClassInfo:
    bases = [_unparse(b) for b in node.bases if _unparse(b) != "object"]
    info = ClassInfo(name=node.name, module=module, bases=bases)
    info.is_abstract = any(b in ("ABC", "ABCMeta") or b.endswith("ABC") for b in bases)
    for stmt in node.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            info.methods.append(_method(stmt))
            if any(_call_name(d) == "abstractmethod" for d in stmt.decorator_list):
                info.is_abstract = True
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            name = stmt.target.id
            if name.startswith("__"):
                continue
            if _mapped_inner(stmt.annotation) is not None:
                continue  # ER-колонка — не дублируем в атрибуты класса
            info.attributes.append(Attribute(name=name, type=_unparse(stmt.annotation)))
    return info


def _method(node: ast.FunctionDef | ast.AsyncFunctionDef) -> Method:
    args = [a.arg for a in node.args.args if a.arg not in ("self", "cls")]
    if node.args.vararg:
        args.append("*" + node.args.vararg.arg)
    if node.args.kwarg:
        args.append("**" + node.args.kwarg.arg)
    name = node.name
    visibility = "private" if name.startswith("__") and not name.endswith("__") else (
        "protected" if name.startswith("_") else "public"
    )
    return Method(
        name=name,
        args=args,
        returns=_unparse(node.returns) if node.returns is not None else None,
        is_async=isinstance(node, ast.AsyncFunctionDef),
        visibility=visibility,
    )


# ---- small AST helpers ----------------------------------------------------

def _call_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _is_true(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and node.value is True


def _clean_type(node: ast.expr) -> tuple[str, bool]:
    """Текст типа + признак nullable (``X | None`` / ``Optional[X]``)."""
    text = _unparse(node)
    nullable = False
    if "None" in text:
        nullable = True
        text = text.replace("| None", "").replace("None |", "").strip()
        if text.startswith("Optional[") and text.endswith("]"):
            text = text[len("Optional["):-1]
    return text.strip(), nullable


def _unparse(node: ast.expr | None) -> str:
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except Exception:
        return ""
