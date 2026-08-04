"""
Phase 6.5: Fractal Extraction Pattern.

FractalExtractor analyzes an archtool module's dependency graph and produces an
ExtractPlan — a dry-run description of what would be generated:
  - new standalone microservice project
  - inner_integrations/<module>/ HTTP/gRPC/Kafka client in the monolith

Actual file generation is done by CLI `wf extract <module>`.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ModuleDependency:
    name: str
    import_path: str
    is_direct: bool = True


@dataclass
class ExtractPlan:
    module_name: str
    module_path: Path
    protocol: str = "http"
    dependencies: list[ModuleDependency] = field(default_factory=list)
    generated_client_path: Optional[Path] = None
    generated_service_path: Optional[Path] = None

    def has_circular_deps(self) -> bool:
        seen: set[str] = set()
        stack = [d.import_path for d in self.dependencies]
        while stack:
            dep = stack.pop()
            if dep == self.module_name:
                return True
            if dep not in seen:
                seen.add(dep)
        return False

    def summary(self) -> str:
        lines = [f"ExtractPlan: {self.module_name} → {self.protocol}"]
        if self.dependencies:
            lines.append("  Dependencies:")
            for d in self.dependencies:
                direct = " (direct)" if d.is_direct else ""
                lines.append(f"    - {d.import_path}{direct}")
        else:
            lines.append("  No cross-module dependencies found.")
        if self.has_circular_deps():
            lines.append("  WARNING: circular dependencies detected — resolve before extraction")
        return "\n".join(lines)


class FractalExtractor:
    """
    Analyzes an archtool module for extraction readiness.

    Phase 1 implementation: path-based dependency listing.
    Full AST-based import graph analysis is in roadmap.
    """

    @staticmethod
    def analyze(
        module_path: str,
        *,
        protocol: str = "http",
        root: Optional[Path] = None,
    ) -> ExtractPlan:
        """
        Dry-run analysis: returns ExtractPlan without touching any files.

        Args:
            module_path: dotted module path, e.g. "app.orders"
            protocol: target transport ("http", "grpc", "kafka")
            root: project root (default: cwd)
        """
        root = root or Path.cwd()
        path = root / Path(module_path.replace(".", "/"))

        plan = ExtractPlan(
            module_name=module_path,
            module_path=path,
            protocol=protocol,
            generated_client_path=root / "inner_integrations" / path.name,
            generated_service_path=Path(f"{path.name}-service"),
        )

        interfaces_file = path / "interfaces.py"
        if interfaces_file.exists():
            plan.dependencies = FractalExtractor._scan_imports(interfaces_file, module_path)

        return plan

    @staticmethod
    def _scan_imports(file: Path, own_module: str) -> list[ModuleDependency]:
        """Lightweight import scanner — finds `from app.*` imports in the file."""
        deps: list[ModuleDependency] = []
        try:
            source = file.read_text()
        except OSError:
            return deps

        import ast
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return deps

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                mod = node.module
                if mod.startswith("app.") and mod != own_module:
                    deps.append(ModuleDependency(
                        name=mod.split(".")[-1],
                        import_path=mod,
                        is_direct=True,
                    ))
        return deps

    @staticmethod
    def extract(plan: ExtractPlan) -> None:
        """
        Execute extraction.

        Generates:
          - inner_integrations/<module>/ with protocol client
          - <module>-service/ standalone project skeleton
        """
        raise NotImplementedError(
            "Full file generation is in roadmap. "
            "Use FractalExtractor.analyze() with --dry-run to inspect the plan."
        )
