"""
Phase 3.6: Meta-programming — runtime class generation.

generate() creates concrete Repo/Service subclasses with model/dm_class pre-wired.
The CLI command `wf generate impl` uses this to write actual .py files.

Usage (runtime mode):
    result = generate(model=User, datamapper=UserDM)
    # result.repo is UserRepo(GenericRepo) with model=User, dm_class=UserDM

Usage (code generation mode — via CLI):
    wf generate impl app.users
    # writes repos.py, services.py with concrete subclasses
"""
from dataclasses import dataclass
from pathlib import Path
from types import new_class
from typing import Any, Optional, Type


@dataclass
class GenerationResult:
    model: Type
    dm_class: Type
    repo: Type
    service: Type
    create_dto: Optional[Type] = None
    update_dto: Optional[Type] = None
    selection: Optional[Type] = None

    @property
    def model_name(self) -> str:
        return self.model.__name__


def generate(
    model: Type,
    datamapper: Type,
    create: Optional[Type] = None,
    update: Optional[Type] = None,
    selection: Optional[Type] = None,
    module_path: Optional[Path] = None,
) -> GenerationResult:
    """
    Generate concrete GenericRepo and GenericService subclasses at runtime.

    Args:
        model:      SQLAlchemy ORM model class
        datamapper: Pydantic DM/DTO class for serialization
        create:     DTO for create operations (optional)
        update:     DTO for update operations (optional)
        selection:  FilterBase subclass (optional)
        module_path: source module path (used by CLI code generation)
    """
    from web_fractal.mixins import GenericRepo, GenericService

    name = model.__name__

    repo_cls = new_class(
        f"{name}Repo",
        bases=(GenericRepo,),
        exec_body=lambda ns: ns.update({"model": model, "dm_class": datamapper}),
    )

    service_cls = new_class(
        f"{name}Service",
        bases=(GenericService,),
        exec_body=lambda ns: None,
    )

    return GenerationResult(
        model=model,
        dm_class=datamapper,
        repo=repo_cls,
        service=service_cls,
        create_dto=create,
        update_dto=update,
        selection=selection,
    )


def register_generated_results(injector: Any, result: GenerationResult) -> None:
    """
    Register a GenerationResult with an archtool DependencyInjector.

    Creates repo/service instances, wires repo into service, registers both.
    """
    repo_instance = result.repo()
    service_instance = result.service()
    service_instance.repo = repo_instance

    repo_key = type(repo_instance).__name__
    service_key = type(service_instance).__name__

    if hasattr(injector, "register"):
        injector.register(repo_key, repo_instance)
        injector.register(service_key, service_instance)
    elif hasattr(injector, "_reg_dependency"):
        injector._reg_dependency(repo_key, repo_instance)
        injector._reg_dependency(service_key, service_instance)
