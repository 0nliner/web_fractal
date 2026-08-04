import pathlib
from typing import Optional, TypeVar
from inspect import isclass

from archtool.dependency_injector import DependencyInjector
from archtool.utils import get_subclasses_from_module

from fastapi import FastAPI
from sqlalchemy.orm import DeclarativeBase

from typing import Callable


T = TypeVar("T")


def filter_objects_of_type(injector: DependencyInjector, obj_type: T) -> list[T]:
    # archtool 2.0 переименовал приватное _dependencies в публичное dependencies.
    # Чтение приватного имени под 2.x возвращало ноль объектов, и приложение
    # поднималось с пустым роутером — без единой ошибки. Проверка именно на None,
    # а не на истинность: пустой словарь зависимостей легален и не должен уводить
    # на ветку совместимости.
    dependencies = getattr(injector, "dependencies", None)
    if dependencies is None:
        dependencies = getattr(injector, "_dependencies", {})

    result = []
    for key, value in dependencies.items():
        if isclass(type(value)) and isinstance(value, obj_type):
            result.append(value)
    return result


def initialize_controllers_api(injector: DependencyInjector, app: Optional[FastAPI] = None):
    from .cli.interfaces import CommanderControllerABC
    from .http.interfaces import HttpControllerABC

    if app:
        http_initializers = filter_objects_of_type(injector, HttpControllerABC)
        for http_initializer in http_initializers:
            http_initializer.init_http_routes()
            app.include_router(http_initializer.router)

    command_initializers = filter_objects_of_type(injector, CommanderControllerABC)
    for command_initializer in command_initializers:
        command_initializer.reg_commands()


def import_all_models(Base) -> list[DeclarativeBase]:
    from archtool.utils import get_project_root

    try:
        from app.archtool_conf.custom_layers import APPS
    except ImportError:
        import warnings
        warnings.warn("import_all_models: APPS not found, returning empty list")
        return []

    root = get_project_root()
    all_models = []
    for app in APPS:
        modules_path = root / pathlib.Path(app.import_path.replace('.', '/')) / 'models.py'
        if not modules_path.exists():
            continue
        import_path = f"{app.import_path}.models"
        models = get_subclasses_from_module(module_path=import_path, superclass=Base)
        all_models.extend(models)
    return list(set(all_models))
