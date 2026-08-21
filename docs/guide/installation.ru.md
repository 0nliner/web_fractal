# Установка

```bash
pip install web_fractal
```

Нужен Python 3.12+.

## Экстры

Ядро не импортирует веб-фреймворк. Всё, что привязано к конкретному фреймворку,
вынесено в экстры:

| Экстра | Что ставит | Для чего |
|---|---|---|
| `fastapi` | `fastapi` | `web_fractal.http.*`, `building_utils`, `middlewares` |
| `aiohttp` | `aiohttp` | `utils.download_large_file` |
| `kafka` | `aiokafka` | `KafkaControllerABC` |
| `grpc` | `grpclib` | `GrpcServiceControllerABC` |
| `graphql` | `strawberry-graphql` | `GraphQLControllerABC` |
| `django` | `django` | `web_fractal.django` |

```bash
pip install "web_fractal[fastapi]"
```

!!! note "Почему экстры здесь важны"
    До 0.2.1 `utils.py` импортировал `aiohttp` и `fastapi` на уровне модуля, а
    `db.py` импортирует `utils`. Из-за этого `import web_fractal.db` — самый
    ходовой модуль библиотеки — требовал веб-фреймворка. Теперь импорты ленивые,
    и экстры значат то, что написано.

## Зависимости ядра

`pydantic`, `sqlalchemy`, `archtool`, `click`, `furl`, `pytz`,
`typing-extensions`. Они ставятся автоматически — не перечисляйте их повторно в
своём проекте.

## Ленивое публичное API

Имена импортируются из корня пакета, но резолвятся при первом обращении
(PEP 562):

```python
from web_fractal import UnitOfWork      # web_fractal.db импортируется лениво
import web_fractal
web_fractal.HttpControllerABC           # без [fastapi] бросит ModuleNotFoundError
```

Импорт напрямую из подмодуля — `from web_fractal.db import UnitOfWork` —
равнозначен и чуть явнее.
