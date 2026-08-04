"""
Phase 1 tests: building_utils.py
- filter_objects_of_type uses injector.dependencies (archtool 2.x public API)
- import_all_models returns [] gracefully when APPS not importable
- initialize_controllers_api calls init_http_routes + include_router on HTTP controllers
- initialize_controllers_api calls reg_commands on CLI controllers
"""
import warnings
from unittest.mock import MagicMock, call

import pytest

from web_fractal.building_utils import filter_objects_of_type, import_all_models, initialize_controllers_api


class _TypeA:
    pass


class _TypeB:
    pass


def _make_injector(deps: dict) -> MagicMock:
    injector = MagicMock(spec=[])  # spec=[] → accessing _dependencies raises AttributeError
    injector.dependencies = deps
    return injector


# --- filter_objects_of_type ---

def test_filter_objects_of_type_returns_matching_instances():
    a1, a2 = _TypeA(), _TypeA()
    b1 = _TypeB()
    injector = _make_injector({"k1": a1, "k2": b1, "k3": a2})

    result = filter_objects_of_type(injector, _TypeA)

    assert set(result) == {a1, a2}


def test_filter_objects_of_type_empty_when_no_match():
    injector = _make_injector({"k": _TypeB()})
    result = filter_objects_of_type(injector, _TypeA)
    assert result == []


def test_filter_objects_of_type_empty_dependencies():
    injector = _make_injector({})
    result = filter_objects_of_type(injector, _TypeA)
    assert result == []


def test_filter_objects_of_type_does_not_use_private_dependencies():
    """Must use injector.dependencies, not injector._dependencies (archtool 2.x broke this)."""
    injector = MagicMock(spec=[])
    injector.dependencies = {}
    filter_objects_of_type(injector, _TypeA)
    # _dependencies must never be accessed
    assert not hasattr(injector, '_dependencies') or not injector._dependencies.called


# --- import_all_models ---

def test_import_all_models_returns_empty_when_apps_not_found():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = import_all_models(object)
    assert result == []
    assert any("APPS" in str(w.message) for w in caught)


# --- initialize_controllers_api ---

def test_initialize_controllers_api_http():
    from web_fractal.http.interfaces import HttpControllerABC

    controller = MagicMock(spec=HttpControllerABC)
    controller.router = MagicMock()
    app = MagicMock()
    injector = _make_injector({"ctrl": controller})

    initialize_controllers_api(injector, app=app)

    controller.init_http_routes.assert_called_once()
    app.include_router.assert_called_once_with(controller.router)


def test_initialize_controllers_api_no_app_skips_http():
    from web_fractal.http.interfaces import HttpControllerABC

    controller = MagicMock(spec=HttpControllerABC)
    injector = _make_injector({"ctrl": controller})

    initialize_controllers_api(injector, app=None)

    controller.init_http_routes.assert_not_called()


def test_initialize_controllers_api_cli():
    from web_fractal.cli.interfaces import CommanderControllerABC

    controller = MagicMock(spec=CommanderControllerABC)
    injector = _make_injector({"cmd": controller})

    initialize_controllers_api(injector, app=None)

    controller.reg_commands.assert_called_once()
