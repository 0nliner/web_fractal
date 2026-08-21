# Extraction

Turning a module of a monolith into a standalone service is mostly mechanical
and mostly the same every time: find what the module depends on, find who
depends on it, generate a project, and replace the in-process calls with a
client.

```bash
wf extract orders            # dry run: prints the plan, changes nothing
wf extract orders -p grpc --no-dry-run
```

## The plan

`FractalExtractor` walks the archtool dependency graph of the module and
produces an `ExtractPlan` describing:

* the standalone service project to be generated;
* `inner_integrations/<module>/` in the monolith — an HTTP, gRPC or Kafka client
  with the same interface the module had, so callers keep calling the same ABC;
* the dependencies that come along, and the ones that would have to be broken.

```python
from web_fractal.core.extraction import FractalExtractor

plan = FractalExtractor(...).build_plan("orders")
```

Dry run is the default deliberately: the plan is the useful part. Most modules
are not extractable on the first read, and the list of dependencies that would
have to be broken is the actual answer — it tells you what to fix before any
code moves.

## Why the interface survives

Callers depend on the module's ABC, not on its implementation. The generated
client implements the same ABC over the wire, so the call sites do not change —
only what is registered in the injector does. That is the entire point of
declaring interfaces separately, and extraction is where it pays off.
