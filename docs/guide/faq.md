# FAQ

## Do I need archtool?

No. Filters, mixins, security and the Unit of Work work with any wiring —
including none. `building_utils` is the part that assumes an archtool injector.

## Do I need FastAPI?

No. The core imports no web framework; `web_fractal.http.*` lives behind the
`fastapi` extra. Since 0.2.1 `import web_fractal.db` costs you neither FastAPI
nor aiohttp.

## Why does an unknown operator get ignored instead of raising?

Because a query string is user input, and the useful behaviour for
`?name__gte=x` on a string field is a broader result set, not a 500. Operators
that a field *has* but a caller may not use are a different matter — that is
`FilterScope`, and it drops the expression on purpose.

## Can I mix the DSL with raw SQLAlchemy?

Yes. `apply_selection` returns an ordinary `Select`; keep chaining `.where()`,
`.join()`, `.options()` as usual.

## `GenericRepo` does not fit my domain

Override the method that differs. When most of them are overridden, drop the
mixin and write the repository — it is a shortcut, not a contract.

## Why is the public API lazy?

`__init__` used to import every submodule, which meant the FastAPI and archtool
integrations were pulled in by any import at all. Now names resolve on first
access (PEP 562), and the extras are honest. `from web_fractal import X` still
works; type checkers see the real imports through a `TYPE_CHECKING` block.

## Which Python?

3.12+. Note that on 3.14 lazy annotations (PEP 649) break archtool's dependency
discovery, so a project using both should pin `<3.13` until archtool adapts.

## The app starts but every request fails on a missing dependency

Almost always a module missing from the injector's module list. `wf validate`
catches it; the application itself will not, because an unwired dependency is
only touched on the first request.
