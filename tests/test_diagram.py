"""Tests for `wf diagram` — reverse-engineering ER + class diagrams from code
via static AST parsing (web_fractal.core.diagram)."""
import json

import pytest

from web_fractal.core.diagram import build_diagrams, render, to_cad

FIXTURE = '''
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, DateTime
from web_fractal.db import Base


class TimestampMixin:
    created_at: Mapped[str] = mapped_column(DateTime)


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Order(Base, TimestampMixin):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # relationship — ORM-навигация, НЕ колонка
    user: Mapped["User"] = relationship()


from abc import abstractmethod


class UserServiceABC:
    repo: object

    @abstractmethod
    async def get_by_id(self, id: int) -> User: ...


class UserService(UserServiceABC):
    repo: object

    async def get_by_id(self, id: int) -> User:
        return None

    def _helper(self) -> None: ...
'''


@pytest.fixture()
def model(tmp_path):
    (tmp_path / "sample.py").write_text(FIXTURE)
    return build_diagrams(tmp_path)


def test_entities_and_tables(model):
    tables = {e.table for e in model.entities}
    assert tables == {"users", "orders"}


def test_inherited_column_from_mixin(model):
    order = next(e for e in model.entities if e.table == "orders")
    names = [f.name for f in order.fields]
    # created_at приходит из TimestampMixin, user_id — свой; relationship `user` исключён
    assert "created_at" in names
    assert "user_id" in names
    assert "user" not in names


def test_primary_key_and_nullable(model):
    user = next(e for e in model.entities if e.table == "users")
    by = {f.name: f for f in user.fields}
    assert by["id"].primary_key is True
    assert by["email"].nullable is True
    assert by["name"].nullable is False


def test_foreign_key_relation(model):
    rels = [(r.src_table, r.src_field, r.dst_table, r.dst_field) for r in model.relations]
    assert ("orders", "user_id", "users", "id") in rels


def test_class_inheritance_and_abstract(model):
    svc = next(c for c in model.classes if c.name == "UserService")
    assert "UserServiceABC" in svc.bases
    abc = next(c for c in model.classes if c.name == "UserServiceABC")
    assert abc.is_abstract is True


def test_method_signature_and_visibility(model):
    svc = next(c for c in model.classes if c.name == "UserService")
    by = {m.name: m for m in svc.methods}
    assert by["get_by_id"].is_async is True
    assert by["get_by_id"].args == ["id"]
    assert by["get_by_id"].returns == "User"
    assert by["_helper"].visibility == "protected"


def test_render_mermaid(model):
    out = render(model, fmt="mermaid", kind="both")
    assert "erDiagram" in out
    assert "classDiagram" in out
    assert "orders }o--|| users" in out
    assert "UserServiceABC <|-- UserService" in out


def test_render_cad_json(model):
    out = render(model, fmt="cad", kind="both")
    data = json.loads(out)
    assert {t["name"] for t in data["erd_schema"]["tables"]} == {"users", "orders"}
    # связь по FK разрешена (dst-поле users.id существует)
    assert len(data["erd_schema"]["relations"]) == 1
    assert any(o["obj_type"] == "interface" for o in data["class_schema"]["objects"])


def test_empty_target(tmp_path):
    (tmp_path / "empty.py").write_text("x = 1\n")
    model = build_diagrams(tmp_path)
    assert model.is_empty
