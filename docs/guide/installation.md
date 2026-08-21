# Installation

```bash
pip install web_fractal
```

Python 3.12+ is required.

## Extras

The core imports no web framework. Everything framework-specific is an extra:

| Extra | Pulls in | Needed for |
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

!!! note "Why extras matter here"
    Until 0.2.1 `utils.py` imported `aiohttp` and `fastapi` at module level, and
    `db.py` imports `utils`. That made `import web_fractal.db` — the most used
    module in the library — require a web framework. The imports are lazy now,
    and the extras mean what they say.

## Core dependencies

`pydantic`, `sqlalchemy`, `archtool`, `click`, `furl`, `pytz`,
`typing-extensions`. They are installed for you; do not list them again in your
own project.

## Lazy public API

Names are importable from the package root but resolved on first access
(PEP 562):

```python
from web_fractal import UnitOfWork      # imports web_fractal.db lazily
import web_fractal
web_fractal.HttpControllerABC           # raises ModuleNotFoundError without [fastapi]
```

Importing the submodule directly — `from web_fractal.db import UnitOfWork` — is
equivalent and slightly more explicit.
