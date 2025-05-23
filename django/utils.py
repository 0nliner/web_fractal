from io import BytesIO
from typing import TYPE_CHECKING
from archtool.dependency_injector import DependencyInjector
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.conf import settings
from fastapi import UploadFile

if TYPE_CHECKING:
    from apps.archtool_bundle.apps import ArchtoolBundleConfig



def get_archtools_config() -> 'ArchtoolBundleConfig':
    app_config = apps.get_app_config('archtool_bundle')
    return app_config


def get_injector() -> DependencyInjector:
    app_config = get_archtools_config()
    return app_config.injector



def fastapi_file_to_django_file(file: UploadFile) -> InMemoryUploadedFile:
    """
    Преобразует fastapi.UploadFile в django.core.files.uploadedfile.InMemoryUploadedFile
    """
    # Считываем содержимое файла из FastAPI
    content = file.file.read()

    # Создаём объект InMemoryUploadedFile
    django_file = InMemoryUploadedFile(
        file=BytesIO(content),         # потоко-ориентированный объект из прочитанного контента
        field_name=None,              # имя поля формы (необязательно)
        name=file.filename,           # имя файла
        content_type=file.content_type, 
        size=len(content), 
        charset=None
    )

    # По необходимости можно закрыть исходный файл,
    # если он больше не нужен и не будет использоваться в дальнейшем
    file.file.close()
    
    return django_file


def get_serialized_settings() -> dict[str, Any]:
    context = {}
    for key, value in vars(settings).items():
        if key not in __builtins__:
            serialuzed_value = value if type(value) in __builtins__ else str(value)
            context[key] = serialuzed_value
    return context
