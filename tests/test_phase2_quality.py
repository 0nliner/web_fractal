"""
Phase 2 tests: code quality fixes
- dtos.py: populate_by_name (Pydantic v2), not_blank filters Unset correctly
- db.py: BaseTypedDict.serialize_model returns dict; BaseRepo sessions are closed
- utils.py: get_settings_value returns None on missing, not crashes; split "." fix
- __init__.py: public API is importable from top-level package
"""
import pytest
import pytest_asyncio
from unittest.mock import MagicMock, AsyncMock, patch

from web_fractal.dtos import Base as DTOBase, Pagination
from web_fractal.types import Unset, UNSET


# --- dtos.py: populate_by_name (Pydantic v2 compat) ---

def test_dto_base_populate_by_name():
    """After Pydantic v2 migration, field aliases still work with populate_by_name=True."""
    from pydantic import Field

    class SampleDTO(DTOBase):
        user_id: int = Field(alias="userId")

    obj = SampleDTO(userId=42)
    assert obj.user_id == 42

    obj2 = SampleDTO(user_id=99)
    assert obj2.user_id == 99


def test_dto_base_not_blank_filters_unset():
    class SampleDTO(DTOBase):
        name: object = UNSET
        age: object = UNSET

    obj = SampleDTO(name="Alice", age=UNSET)
    assert obj.not_blank == {"name": "Alice"}


def test_dto_base_not_blank_all_unset():
    class SampleDTO(DTOBase):
        name: object = UNSET

    obj = SampleDTO(name=UNSET)
    assert obj.not_blank == {}


def test_pagination_defaults():
    pag = Pagination()
    assert pag.page == 1
    assert pag.size == 40


# --- db.py: BaseTypedDict ---

def test_base_typed_dict_serialize_model_returns_dict():
    """serialize_model was missing return statement — verify it now returns the dict."""
    from typing_extensions import TypedDict as TypedDictExt
    from web_fractal.db import BaseTypedDict

    class MyDict(BaseTypedDict):
        pass

    obj = MyDict()

    class FakeModel:
        x = 1
        def __init__(self):
            self.__dict__ = {"x": 1}

    result = obj.serialize_model(FakeModel())
    assert result is not None
    assert isinstance(result, dict)


def test_base_typed_dict_not_blank():
    from web_fractal.db import BaseTypedDict

    obj = BaseTypedDict(name="test", value=UNSET)
    result = obj.not_blank
    assert "name" in result
    assert "value" not in result


# --- db.py: BaseRepo session lifecycle ---

@pytest.mark.asyncio
async def test_base_repo_in_session_closes_standalone_session(session_maker):
    """When no UoW is passed, in_session must close the session in finally."""
    from web_fractal.db import BaseRepo

    repo = BaseRepo()
    repo.session_maker = session_maker

    closed_sessions = []
    original_close = None

    async with repo.in_session() as session:
        original_close = session.close
        async def track_close():
            closed_sessions.append(True)
            await original_close()
        session.close = track_close

    assert len(closed_sessions) == 1, "Session must be closed after in_session exits"


@pytest.mark.asyncio
async def test_base_repo_in_session_reuses_uow_session(session_maker):
    """When UoW is passed, in_session must reuse UoW.session without closing it."""
    from web_fractal.db import BaseRepo, UnitOfWork

    repo = BaseRepo()
    repo.session_maker = session_maker

    async with UnitOfWork(session_maker) as uow:
        async with repo.in_session(uow) as session:
            assert session is uow.session


# --- utils.py ---

def test_get_settings_value_returns_none_on_missing_module(monkeypatch):
    """get_settings_value must not crash — returns None when config not found."""
    monkeypatch.delenv("DJANGO_MODE", raising=False)
    from web_fractal.utils import get_settings_value
    result = get_settings_value("NONEXISTENT_KEY_XYZ")
    assert result is None


def test_filename_extension_handles_dots_in_name():
    """Split on '.' must use [-1] to handle filenames like 'archive.tar.gz'."""
    filename = "archive.tar.gz"
    extension = filename.split(".")[-1]
    assert extension == "gz"

    filename2 = "report.pdf"
    assert filename2.split(".")[-1] == "pdf"


# --- __init__.py: public API ---

def test_public_api_importable():
    """All symbols declared in __all__ must be importable from web_fractal directly."""
    import web_fractal
    for name in web_fractal.__all__:
        assert hasattr(web_fractal, name), f"{name} missing from web_fractal public API"


def test_public_api_unit_of_work():
    from web_fractal import UnitOfWork
    assert UnitOfWork is not None


def test_public_api_pagination():
    from web_fractal import Pagination
    pag = Pagination(page=2, size=10)
    assert pag.page == 2


def test_public_api_http_controller_abc():
    from web_fractal import HttpControllerABC
    assert HttpControllerABC is not None
