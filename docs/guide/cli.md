# CLI

The `wf` command ships with the package.

```bash
wf --help
```

## Scaffolding

```bash
wf init myproject                       # new project skeleton
wf init myproject -p http -p kafka      # with several transports

wf add-module orders                    # new domain module
wf add-module orders --with-controller http
wf add-module orders --app backend      # if the package is not "app"
```

`init` lays out the project; `add-module` adds a bounded context inside an
existing one. Both accept the protocols you actually intend to serve, so the
generated controller matches the transport instead of being an HTTP stub you
rewrite.

## Checking the wiring

```bash
wf validate                             # DI wiring + protocol controllers
wf validate --bundle app.archtool_conf.bundle
```

`validate` assembles the injector and reports what did not resolve. Worth a
place in CI: a missing module registration produces an application that starts
fine and fails on the first request, which is exactly the failure mode a test
suite tends to miss.

```bash
wf graph                                # dependency tree
wf graph --format dot | dot -Tpng -o deps.png
wf graph --format web
```

## Diagrams from existing code

```bash
wf diagram app                          # whole package
wf diagram app/orders/models.py -k er
wf diagram app -k class -f mermaid -o docs/classes.md
```

| Option | Values |
|---|---|
| `-k, --kind` | `er`, `class`, `both` (default) |
| `-f, --format` | `mermaid` (default), `cad`, `json` |
| `-o, --out` | write to a file instead of stdout |

The parse is **static** (AST): the target package is never imported, so building
a picture does not require its dependencies, its settings or a live database.

## Extraction

```bash
wf extract orders                       # dry run by default
wf extract orders -p grpc --no-dry-run
```

See [Extraction](extraction.md).
