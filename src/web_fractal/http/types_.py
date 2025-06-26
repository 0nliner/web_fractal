
from typing import Any, Callable, Dict, Optional, Sequence, Set, Type, Union
from enum import Enum
from fastapi.datastructures import DefaultPlaceholder
from fastapi.types import IncEx
from typing_extensions import TypedDict
from fastapi import APIRouter, params
from fastapi.responses import JSONResponse, Response
from fastapi.routing import APIRoute


class RegRoutesParams(TypedDict, total=False):
    path: str
    endpoint: Callable[..., Any]
    response_model: Any
    status_code: Optional[int]
    tags: Optional[list[Union[str, Enum]]]
    dependencies: Optional[Sequence[params.Depends]]
    summary: Optional[str]
    description: Optional[str]
    response_description: str
    responses: Optional[Dict[Union[int, str], Dict[str, Any]]]
    deprecated: Optional[bool]
    methods: Optional[Union[Set[str], list[str]]]
    operation_id: Optional[str]
    response_model_include: Optional[IncEx]
    response_model_exclude: Optional[IncEx]
    response_model_by_alias: bool
    response_model_exclude_unset: bool
    response_model_exclude_defaults: bool
    response_model_exclude_none: bool
    include_in_schema: bool
    response_class: Union[Type[Response], DefaultPlaceholder]
    name: Optional[str]
    route_class_override: Optional[Type[APIRoute]]
    callbacks: Any
    openapi_extra: Optional[Dict[str, Any]]
    generate_unique_id_function: Union[Callable[[APIRoute], str], DefaultPlaceholder]
