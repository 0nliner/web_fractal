import pathlib
from typing import Optional, TypeVar
from inspect import isclass, signature

from archtool.dependency_injector import DependencyInjector
from archtool.utils import get_subclasses_from_module

from fastapi import FastAPI
from sqlalchemy.orm import DeclarativeBase

from .utils import get_settings_value

if get_settings_value("DJANGO_MODE"):
    # from django.apps import apps
    # from django.urls import path
    # from metall_crm.settings import INSTALLED_APPS
    from apps.archtool_bundle.layers import RoutersInitializationStrategyABC

else:
    try:
        from app.archtool_conf.custom_layers import APPS
        from web_fractal.http.interfaces import HttpControllerABC
    except:
        import warnings
        warnings.warn("cli mode used")

from typing import Callable


T = TypeVar("T")


def filter_objects_of_type(injector: DependencyInjector, obj_type: T) -> list[T]:
    result = []
    for key, value in injector._dependencies.items():
        if isclass(type(value)) and isinstance(value, obj_type):
            result.append(value)
    return result


def initialize_controllers_api(injector: DependencyInjector, app: Optional[FastAPI] = None):
    from .cli.interfaces import CommanderControllerABC
    if app:
        http_initializers = filter_objects_of_type(injector, HttpControllerABC)
        for http_initializer in http_initializers:
            http_initializer.init_http_routes()
            app.include_router(http_initializer.router)

    commands_initializer = filter_objects_of_type(injector, CommanderControllerABC)
    for commands_initializer in commands_initializer:
        commands_initializer.reg_commands()



def get_fastapi_app():
    ...


def import_all_models(Base) -> list[DeclarativeBase]:
    all_models = []
    for app in APPS:
        modules_path = "." / pathlib.Path(app.import_path.replace('.', '/')) / 'models.py' 
        if not modules_path.exists(): continue
        import_path = f"{app.import_path}.models"
        models = get_subclasses_from_module(module_path=import_path, superclass=Base)
        all_models.extend(models)
    return list(set(all_models))



def create_functional_wrapper(handler: Callable, controller) -> Callable:
    def wrapper(*args, **kwargs):
        # self=controller, 
        return handler(*args, **kwargs)
    mock_signature = signature(handler)
    wrapper.name = handler.name
    wrapper.signature = mock_signature
    return wrapper
