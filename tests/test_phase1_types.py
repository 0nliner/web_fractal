"""
Phase 1 tests: types.py
- Unset class: duplicate __bool__ removed, classmethod uses cls not self
- UNSET sentinel evaluates to False
- DTOField / OneOrMultuple type aliases exist
"""
from web_fractal.types import Unset, UNSET, DTOField, OneOrMultuple


def test_unset_instance_is_falsy():
    instance = Unset()
    assert bool(instance) is False
    assert not instance


def test_unset_sentinel_is_unset_instance():
    assert isinstance(UNSET, Unset)


def test_unset_used_in_not_blank_filter():
    """Core usage: filtering out UNSET values from a dict."""
    data = {"a": 1, "b": UNSET, "c": "hello", "d": Unset()}
    not_blank = {k: v for k, v in data.items() if v is not UNSET and not isinstance(v, Unset)}
    assert not_blank == {"a": 1, "c": "hello"}


def test_dto_field_type_alias_exists():
    assert DTOField is not None


def test_one_or_multiple_type_alias_exists():
    assert OneOrMultuple is not None
