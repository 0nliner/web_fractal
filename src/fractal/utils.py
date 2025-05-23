from io import BytesIO
import json
import os
from typing import Any, Optional, Union, overload
import aiohttp
import datetime
from pathlib import Path
import importlib

from fastapi import Request
import pytz

from .env_helpers import get_bool_from_env


def get_settings_value(key: str):
    try:
        project_name = Path.cwd().name
        if get_bool_from_env("DJANGO_MODE"):
            settings = importlib.import_module(f"{project_name}.settings")
        else:
            try:
                from app import config as settings
            # TODO: убрать костыль
            except ModuleNotFoundError:
                from dp import config as settings
        result = getattr(settings, key)
        return result
    except:
        return None


def get_settings_values(keys: list[str]) -> list[Any]:
    project_name = Path.cwd().name
    if get_bool_from_env("DJANGO_MODE"):
        settings = importlib.import_module(f"{project_name}.settings")
    else:
        from app import config as settings
    result = [getattr(settings, key) for key in keys]
    return result


async def download_large_file(url: str,
                              save_dir: Path) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise Exception(f"Failed to download file: {response.status}")
            cd_header = response.headers.get('Content-Disposition')
            if cd_header:
                filename = cd_header.split('filename=')[-1].strip('\"')
            else:
                filename = Path(url).name
            extension = filename.split(".")[1]
            filename = f"{datetime.now()}.{extension}".replace(" ", "_")
            save_path = Path(save_dir) / filename
            save_path.parent.mkdir(parents=True, exist_ok=True)

            with open(save_path, 'wb') as f:
                async for chunk in response.content.iter_chunked(1024 * 1024):  # 1 MB chunks
                    f.write(chunk)
            return filename

def map_to_dict(keys, values, **kwargs):
    for value in values:
        prepared = dict(zip(keys, value))
        for key, generator in kwargs.items():
            prepared[key] = list(generator(prepared[key]))
        yield prepared

async def serialize_fastapi_request(request: Request) -> dict:
    request_serialized = {}
    # Считываем тело запроса в байтах
    # Попытаемся распарсить его как JSON, если не получится, оставим как строку
    try:
        body_bytes = ""
        body_bytes = await request.body()
        try:
            body = json.loads(body_bytes)
        except json.JSONDecodeError:
            body = body_bytes.decode("utf-8")
    except Exception as ex:
        body = None

    # Составляем структуру для лога
    request_serialized = {
        "method": request.method,
        "url": str(request.url),  # URL целиком, включая query-параметры
        "headers": str(dict(request.headers)),
        "cookies": request.cookies,
        "query_params": str(dict(request.query_params)),
        "path_params": request.path_params,
        "body": body}
    return request_serialized

from zoneinfo import ZoneInfo

def now() -> datetime.datetime:
    """
    вычисляет текущее время относительно часового пояса
    """
    moscow_tz = pytz.timezone('Europe/Moscow')
    result = moscow_tz.localize(datetime.datetime.now())
    return result

import typing as t
from pydantic import BaseModel, TypeAdapter
# from typing_extensions import TypedDict as TypedDictExt

# T = t.TypeVar("T", bound=BaseModel)
T = t.TypeVar("T")


def serialize_typed_dict(_type: type[T], data: t.Any, as_list: Optional[bool] = None) -> T | list[T]:
    data_as_dict: dict
    if hasattr(data, "__dict__"):
        data_as_dict = data.__dict__ 
    else:
        data_as_dict = data
    data_as_dict = {key: value for key, value in data_as_dict.items() if not key.startswith('_')}
    # result = {key: value for key, value in data.__dict__.items() if not key.startswith('_')}
    # result = {key: value for key, value in data_as_dict.items() if not key.startswith('_')}
    for key, annotation in t.get_type_hints(_type).items():
        if key not in data_as_dict:
            continue
        if hasattr(annotation, "__args__") and annotation.__args__[0] not in [str, int, float, bool]:
            args = annotation.__args__[0]
            data_as_dict[key] = serialize(args, data_as_dict[key], as_list=True)
        else:
            data_as_dict[key] = data_as_dict[key]
    return data_as_dict

@overload
def serialize(_type: type[T], data: t.Any, as_list: t.Literal[True]) -> list[T]: ...
@overload
def serialize(_type: type[T], data: t.Any, as_list: t.Literal[False]) -> T: ...
@overload
def serialize(_type: type[T], data: t.Any, as_list: None = None) -> T | list[T]: ...

def serialize(_type: type[T], data: t.Any, as_list: Optional[bool] = None) -> T | list[T]:
    if issubclass(_type, dict) and not issubclass(type(data), list):
        result = serialize_typed_dict(_type, data, as_list=False)
        return result

    # and hasattr(data[0], "__dict__")
    elif issubclass(_type, dict) and len(data) > 0  and issubclass(type(data), list):
        results = []
        for e in data:
            results.append(serialize_typed_dict(_type, e, as_list=False))
            # result = {key: value for key, value in e.__dict__.items() if not key.startswith('_')}
            # results.append(result)
        return results
    try:
        records_quantity = len(data)
    except TypeError:
        records_quantity = 1

    if records_quantity == 1 or as_list is False:
        try:
            serialized_result = _type.model_validate(data[0] if isinstance(data, (list, tuple)) else data)
        except (TypeError, IndexError):
            serialized_result = _type.model_validate(data)
    elif records_quantity > 1:
        adapter = TypeAdapter(list[_type])
        serialized_result = adapter.validate_python(data)
    else:
        serialized_result = []

    if as_list and not isinstance(serialized_result, list):
        serialized_result = [serialized_result]
    elif as_list is False and isinstance(serialized_result, list):
        if len(serialized_result) == 1:
            serialized_result = serialized_result[0]
        else:
            raise ValueError("Cannot return single item when multiple items exist")

    return serialized_result
