"""web_fractal — конструктор веб-приложений поверх SQLAlchemy и Pydantic.

Публичное API перечислено в `__all__` и доступно как `from web_fractal import X`,
но **подмодули не импортируются на загрузке пакета** (PEP 562): имя
резолвится в момент первого обращения.

Зачем так. Раньше `__init__` тянул всё сразу — включая интеграции с FastAPI и
archtool. Из-за этого `import web_fractal.db`, самый ходовой модуль библиотеки,
требовал установленных `fastapi` и `aiohttp`, хотя ни то ни другое ему не
нужно: пакет, объявленный framework-agnostic, не ставился без веб-фреймворка.
Теперь необязательное остаётся необязательным — за `fastapi`-часть отвечает
экстра `web_fractal[fastapi]`, за транспорты — свои экстры.

Для IDE и статических анализаторов настоящие импорты перечислены в блоке
`TYPE_CHECKING` ниже: подсказки и переход к определению работают как прежде.
"""
import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover — только для анализаторов
    from .db import (  # noqa: F401
        Base,
        BaseRepo,
        BaseTypedDict,
        Dated,
        UOFParams,
        UnitOfWork,
        apply_filters,
        copy_object,
        get_db_name,
        get_json_hash,
        get_no_db_engine,
        order_by_field,
        paginate,
    )
    from .dtos import (  # noqa: F401
        Context,
        DictWrapper,
        MessageDTO,
        Pagination,
    )
    from .types import (  # noqa: F401
        DTOField,
        OneOrMultuple,
        UNSET,
        Unset,
    )
    from .env_helpers import (  # noqa: F401
        get_bool_from_env,
        get_int_from_env,
        get_list_from_env,
    )
    from .building_utils import (  # noqa: F401
        filter_objects_of_type,
        import_all_models,
        initialize_controllers_api,
    )
    from .http.interfaces import (  # noqa: F401
        HttpControllerABC,
    )
    from .filters import (  # noqa: F401
        FilterBase,
        FilterField,
        Op,
        OrderBy,
        apply_selection,
    )
    from .core.security import (  # noqa: F401
        AccessDenied,
        AccessRule,
        EnvContext,
        FieldDecision,
        FieldNotVisible,
        FieldScope,
        FilterScope,
        OperationNotAllowed,
        RowRule,
        ScopeBase,
        SecurityContext,
        UserPrincipal,
    )
    from .mixins import (  # noqa: F401
        GenericRepo,
        GenericService,
        MultipleFound,
        NotExist,
    )
    from .http.auto_controller import (  # noqa: F401
        AutoHttpController,
    )
    from .core.components import (  # noqa: F401
        GenerationResult,
        generate,
        register_generated_results,
    )
    from .transports import (  # noqa: F401
        GraphQLControllerABC,
        GrpcServiceControllerABC,
        KafkaControllerABC,
        ProtocolControllerABC,
        initialize_all_protocols,
    )
    from .core.extraction import (  # noqa: F401
        ExtractPlan,
        FractalExtractor,
    )

#: Имя экспорта → подмодуль, в котором оно живёт.
_EXPORTS: dict[str, str] = {
    "Base": "db",
    "BaseRepo": "db",
    "BaseTypedDict": "db",
    "Dated": "db",
    "UOFParams": "db",
    "UnitOfWork": "db",
    "apply_filters": "db",
    "copy_object": "db",
    "get_db_name": "db",
    "get_json_hash": "db",
    "get_no_db_engine": "db",
    "order_by_field": "db",
    "paginate": "db",
    "Context": "dtos",
    "DictWrapper": "dtos",
    "MessageDTO": "dtos",
    "Pagination": "dtos",
    "DTOField": "types",
    "OneOrMultuple": "types",
    "UNSET": "types",
    "Unset": "types",
    "get_bool_from_env": "env_helpers",
    "get_int_from_env": "env_helpers",
    "get_list_from_env": "env_helpers",
    "filter_objects_of_type": "building_utils",
    "import_all_models": "building_utils",
    "initialize_controllers_api": "building_utils",
    "HttpControllerABC": "http.interfaces",
    "FilterBase": "filters",
    "FilterField": "filters",
    "Op": "filters",
    "OrderBy": "filters",
    "apply_selection": "filters",
    "AccessDenied": "core.security",
    "AccessRule": "core.security",
    "EnvContext": "core.security",
    "FieldDecision": "core.security",
    "FieldNotVisible": "core.security",
    "FieldScope": "core.security",
    "FilterScope": "core.security",
    "OperationNotAllowed": "core.security",
    "RowRule": "core.security",
    "ScopeBase": "core.security",
    "SecurityContext": "core.security",
    "UserPrincipal": "core.security",
    "GenericRepo": "mixins",
    "GenericService": "mixins",
    "MultipleFound": "mixins",
    "NotExist": "mixins",
    "AutoHttpController": "http.auto_controller",
    "GenerationResult": "core.components",
    "generate": "core.components",
    "register_generated_results": "core.components",
    "GraphQLControllerABC": "transports",
    "GrpcServiceControllerABC": "transports",
    "KafkaControllerABC": "transports",
    "ProtocolControllerABC": "transports",
    "initialize_all_protocols": "transports",
    "ExtractPlan": "core.extraction",
    "FractalExtractor": "core.extraction",
}


def __getattr__(name: str):
    """Ленивый резолв публичного имени (PEP 562)."""
    module = _EXPORTS.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(importlib.import_module(f".{module}", __name__), name)
    # Кладём в globals: следующий доступ идёт напрямую, без __getattr__.
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """`dir(web_fractal)` и автодополнение показывают полное API."""
    return sorted(set(globals()) | set(_EXPORTS))


__all__ = list(_EXPORTS)
