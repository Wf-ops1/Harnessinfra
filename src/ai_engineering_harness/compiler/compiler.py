"""Fail-closed compiler for typed graph specifications."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path, PurePath, PurePosixPath
from typing import Any, cast

import yaml
from pydantic import ValidationError

from ai_engineering_harness.contracts import (
    AgentNodeSpec,
    CompiledGraphArtifact,
    ContractRegistry,
    ContractRegistryError,
    GraphSpec,
    PolicyRegistry,
    PolicyRegistryError,
)
from ai_engineering_harness.versioning import ARTIFACT_SCHEMA_VERSION, PACKAGE_VERSION

_WORKFLOW_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class GraphCompilerError(Exception):
    """Base error for graph compilation."""


class GraphSourceError(GraphCompilerError):
    """The requested YAML source is missing, unsafe, or unreadable."""


class GraphValidationError(GraphCompilerError):
    """The graph or one of its referenced catalogs is invalid."""


class GraphWriteError(GraphCompilerError):
    """The validated artifact could not be written to its canonical destination."""


class GraphCompiler:
    """Compile one YAML graph into the canonical typed artifact."""

    def __init__(self, project_root: Path):
        try:
            resolved_root = Path(project_root).resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise GraphSourceError(f"project root cannot be resolved: {project_root}") from exc
        if not resolved_root.is_dir():
            raise GraphSourceError(f"project root is not a directory: {resolved_root}")

        self.project_root = resolved_root
        self.output_dir = self.project_root / ".harness" / "state" / "compiled"

    def compile_graph(self, yaml_path: Path, workflow_name: str | None = None) -> Path:
        """Validate and compile a graph without producing output on validation failure."""
        source_path = self._resolve_source(yaml_path)
        raw_graph = self._load_yaml_mapping(source_path, source=True)

        try:
            graph = GraphSpec.model_validate(raw_graph)
        except ValidationError as exc:
            raise GraphValidationError(f"invalid graph specification {source_path}: {exc}") from exc

        self._validate_workflow_identity(graph.graph.name, workflow_name)

        contract_references = list(graph.contracts)
        for node in graph.nodes:
            if isinstance(node, AgentNodeSpec):
                contract_references.extend((node.input_contract, node.output_contract))

        try:
            contract_registry = ContractRegistry(
                schema_root=self._contract_schema_root(),
                repository_trusted=False,
                approved_python_contracts=(),
            )
            resolved_contracts = contract_registry.resolve_many(contract_references)
            policy_registry = self._policy_registry()
            resolved_policies = policy_registry.resolve_graph(graph)
            artifact = CompiledGraphArtifact(
                artifact_schema_version=ARTIFACT_SCHEMA_VERSION,
                package_version=PACKAGE_VERSION,
                graph=graph,
                resolved_contracts=resolved_contracts,
                resolved_policies=resolved_policies,
            )
        except (ContractRegistryError, PolicyRegistryError, ValidationError, ValueError) as exc:
            raise GraphValidationError(f"graph references are invalid: {exc}") from exc

        output_file = self.compiled_path(graph.graph.name)
        try:
            self._prepare_output_directory()
            output_file.write_text(
                artifact.model_dump_json(indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )
        except (OSError, UnicodeError, ValueError) as exc:
            raise GraphWriteError(f"cannot write compiled graph {output_file}: {exc}") from exc
        return output_file

    def compiled_path(self, workflow_name: str) -> Path:
        """Return the canonical output path for a safe workflow identifier."""
        self._validate_workflow_name(workflow_name)
        self._validate_existing_output_directories()
        output_file = self.output_dir / f"{workflow_name}.json"
        if output_file.is_symlink():
            raise GraphWriteError(f"compiled graph path cannot be a symlink: {output_file}")
        if output_file.exists():
            try:
                resolved = output_file.resolve(strict=True)
            except (OSError, RuntimeError) as exc:
                raise GraphWriteError(f"cannot resolve compiled graph path: {output_file}") from exc
            if not resolved.is_file() or not resolved.is_relative_to(self.project_root):
                raise GraphWriteError(f"compiled graph path escapes project root: {output_file}")
        return output_file

    def _resolve_source(self, yaml_path: Path) -> Path:
        candidate = Path(yaml_path)
        if not candidate.is_absolute() and ".." in candidate.parts:
            raise GraphSourceError(f"graph source cannot contain traversal: {yaml_path}")
        if candidate.suffix != ".yaml":
            raise GraphSourceError(f"graph source must use the .yaml extension: {yaml_path}")

        joined = candidate if candidate.is_absolute() else self.project_root / candidate
        try:
            resolved = joined.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise GraphSourceError(f"graph source does not exist or cannot be resolved: {yaml_path}") from exc
        if not resolved.is_relative_to(self.project_root):
            raise GraphSourceError(f"graph source escapes project root: {yaml_path}")
        if not resolved.is_file():
            raise GraphSourceError(f"graph source is not a regular file: {resolved}")
        return resolved

    def _policy_registry(self) -> PolicyRegistry:
        try:
            base_registry = PolicyRegistry()
            policy_documents = self._load_policy_overrides(base_registry.available_policies)
            role_documents = self._load_role_overrides()
            tool_document = self._load_optional_mapping(
                self.project_root / ".harness" / "tools" / "tool_registry.yaml",
                allowed_root=self.project_root / ".harness" / "tools",
                label="tool registry override",
            )
            return PolicyRegistry(
                policy_documents=policy_documents or None,
                role_documents=role_documents or None,
                tool_registry_document=tool_document,
            )
        except GraphValidationError:
            raise
        except (OSError, UnicodeError, yaml.YAMLError, PolicyRegistryError, ValidationError) as exc:
            raise GraphValidationError(f"cannot load policy catalogs: {exc}") from exc

    def _contract_schema_root(self) -> Path:
        schema_root = self.project_root / ".harness" / "contracts"
        if not schema_root.exists() and not schema_root.is_symlink():
            return schema_root
        try:
            resolved = schema_root.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise GraphValidationError(f"cannot resolve contract schema root: {schema_root}") from exc
        if not resolved.is_dir() or not resolved.is_relative_to(self.project_root):
            raise GraphValidationError(f"contract schema root escapes project root: {schema_root}")
        return resolved

    def _prepare_output_directory(self) -> None:
        self._validate_existing_output_directories()
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            resolved_output = self.output_dir.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise GraphWriteError(f"cannot create output directory: {self.output_dir}") from exc
        if not resolved_output.is_dir() or not resolved_output.is_relative_to(self.project_root):
            raise GraphWriteError(f"output directory escapes project root: {self.output_dir}")

    def _validate_existing_output_directories(self) -> None:
        current = self.project_root
        for part in (".harness", "state", "compiled"):
            current = current / part
            if current.is_symlink():
                raise GraphWriteError(f"output directory cannot be a symlink: {current}")
            if not current.exists() and not current.is_symlink():
                continue
            try:
                resolved = current.resolve(strict=True)
            except (OSError, RuntimeError) as exc:
                raise GraphWriteError(f"cannot resolve output directory: {current}") from exc
            if not resolved.is_dir() or not resolved.is_relative_to(self.project_root):
                raise GraphWriteError(f"output directory escapes project root: {current}")

    def _load_policy_overrides(
        self,
        available_policies: tuple[str, ...],
    ) -> dict[str, Mapping[str, Any]]:
        policies_root = self.project_root / ".harness" / "policies"
        overrides: dict[str, Mapping[str, Any]] = {}
        for reference in available_policies:
            policy_name = PurePosixPath(reference).name
            document = self._load_optional_mapping(
                policies_root / policy_name,
                allowed_root=policies_root,
                label=f"policy override {reference}",
            )
            if document is not None:
                overrides[reference] = document
        return overrides

    def _load_role_overrides(self) -> dict[str, Mapping[str, Any]]:
        roles_root = self.project_root / ".harness" / "agents"
        if not roles_root.exists() and not roles_root.is_symlink():
            return {}
        try:
            resolved_root = roles_root.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise GraphValidationError(f"cannot resolve agent overrides directory: {roles_root}") from exc
        if not resolved_root.is_dir() or not resolved_root.is_relative_to(self.project_root):
            raise GraphValidationError(f"unsafe agent overrides directory: {roles_root}")

        overrides: dict[str, Mapping[str, Any]] = {}
        try:
            directories = sorted(resolved_root.iterdir(), key=lambda item: item.name)
        except OSError as exc:
            raise GraphValidationError(f"cannot enumerate agent overrides: {exc}") from exc
        for directory in directories:
            if directory.name.startswith("_") or not directory.is_dir():
                continue
            document = self._load_optional_mapping(
                directory / "agent.yaml",
                allowed_root=resolved_root,
                label=f"agent role override {directory.name}",
            )
            if document is None:
                continue
            self._validate_role_prompt(directory, document)
            overrides[directory.name] = document
        return overrides

    def _validate_role_prompt(self, role_directory: Path, document: Mapping[str, Any]) -> None:
        prompt_name = document.get("system_prompt_file")
        if not isinstance(prompt_name, str) or not prompt_name or PurePath(prompt_name).name != prompt_name:
            raise GraphValidationError(
                f"agent role override {role_directory.name!r} has an unsafe system_prompt_file"
            )
        prompt_path = role_directory / prompt_name
        try:
            resolved_prompt = prompt_path.resolve(strict=True)
            resolved_role = role_directory.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise GraphValidationError(
                f"agent role override {role_directory.name!r} references a missing system prompt"
            ) from exc
        if not resolved_prompt.is_file() or not resolved_prompt.is_relative_to(resolved_role):
            raise GraphValidationError(
                f"agent role override {role_directory.name!r} references an unsafe system prompt"
            )

    def _load_optional_mapping(
        self,
        path: Path,
        *,
        allowed_root: Path,
        label: str,
    ) -> dict[str, Any] | None:
        if not path.exists() and not path.is_symlink():
            return None
        try:
            resolved = path.resolve(strict=True)
            resolved_root = allowed_root.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise GraphValidationError(f"cannot resolve {label}: {path}") from exc
        if not resolved.is_relative_to(resolved_root) or not resolved.is_relative_to(self.project_root):
            raise GraphValidationError(f"{label} escapes its allowed directory: {path}")
        if not resolved.is_file():
            raise GraphValidationError(f"{label} is not a regular file: {path}")
        return self._load_yaml_mapping(resolved, source=False)

    @staticmethod
    def _load_yaml_mapping(path: Path, *, source: bool) -> dict[str, Any]:
        error_type = GraphSourceError if source else GraphValidationError
        try:
            loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise error_type(f"cannot read YAML object {path}: {exc}") from exc
        if not isinstance(loaded, Mapping):
            raise error_type(f"YAML document must be a non-empty object: {path}")
        return cast(dict[str, Any], dict(loaded))

    @classmethod
    def _validate_workflow_identity(cls, graph_name: str, workflow_name: str | None) -> None:
        cls._validate_workflow_name(graph_name)
        if workflow_name is None:
            return
        cls._validate_workflow_name(workflow_name)
        if workflow_name != graph_name:
            raise GraphValidationError(
                f"workflow name {workflow_name!r} does not match graph name {graph_name!r}"
            )

    @staticmethod
    def _validate_workflow_name(workflow_name: str) -> None:
        if not isinstance(workflow_name, str) or not _WORKFLOW_NAME_RE.fullmatch(workflow_name):
            raise GraphValidationError(
                "workflow name must match [A-Za-z0-9][A-Za-z0-9._-]*"
            )


__all__ = [
    "GraphCompiler",
    "GraphCompilerError",
    "GraphSourceError",
    "GraphValidationError",
    "GraphWriteError",
]
