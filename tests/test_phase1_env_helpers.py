"""
Phase 1 tests: env_helpers.py
- get_int_from_env: was returning default when var EXISTS (inverted logic), now returns default when ABSENT
- get_bool_from_env: basic coverage
- get_list_from_env: basic coverage
"""
import pytest
from web_fractal.env_helpers import get_int_from_env, get_bool_from_env, get_list_from_env


# --- get_int_from_env (critical fix: inverted logic) ---

def test_get_int_from_env_returns_default_when_var_missing(monkeypatch):
    monkeypatch.delenv("WF_TEST_INT", raising=False)
    assert get_int_from_env("WF_TEST_INT", default=42) == 42


def test_get_int_from_env_parses_env_when_present(monkeypatch):
    monkeypatch.setenv("WF_TEST_INT", "100")
    assert get_int_from_env("WF_TEST_INT", default=42) == 100


def test_get_int_from_env_parses_zero(monkeypatch):
    monkeypatch.setenv("WF_TEST_INT", "0")
    assert get_int_from_env("WF_TEST_INT", default=99) == 0


def test_get_int_from_env_env_overrides_default(monkeypatch):
    monkeypatch.setenv("WF_TEST_INT", "7")
    # The key property: env value must win over default
    result = get_int_from_env("WF_TEST_INT", default=999)
    assert result == 7
    assert result != 999


# --- get_bool_from_env ---

@pytest.mark.parametrize("value", ["true", "True", "TRUE", "1"])
def test_get_bool_from_env_truthy_values(monkeypatch, value):
    monkeypatch.setenv("WF_TEST_BOOL", value)
    assert get_bool_from_env("WF_TEST_BOOL") is True


@pytest.mark.parametrize("value", ["false", "False", "0", "no", ""])
def test_get_bool_from_env_falsy_values(monkeypatch, value):
    monkeypatch.setenv("WF_TEST_BOOL", value)
    assert get_bool_from_env("WF_TEST_BOOL") is False


def test_get_bool_from_env_missing_returns_false(monkeypatch):
    monkeypatch.delenv("WF_TEST_BOOL", raising=False)
    assert get_bool_from_env("WF_TEST_BOOL") is False


# --- get_list_from_env ---

def test_get_list_from_env_comma_separated(monkeypatch):
    monkeypatch.setenv("WF_TEST_LIST", "a,b,c")
    assert get_list_from_env("WF_TEST_LIST") == ["a", "b", "c"]


def test_get_list_from_env_single_value(monkeypatch):
    monkeypatch.setenv("WF_TEST_LIST", "only_one")
    assert get_list_from_env("WF_TEST_LIST") == ["only_one"]


def test_get_list_from_env_missing_returns_empty(monkeypatch):
    monkeypatch.delenv("WF_TEST_LIST", raising=False)
    assert get_list_from_env("WF_TEST_LIST") == []


def test_get_list_from_env_empty_string_returns_empty(monkeypatch):
    monkeypatch.setenv("WF_TEST_LIST", "")
    assert get_list_from_env("WF_TEST_LIST") == []
