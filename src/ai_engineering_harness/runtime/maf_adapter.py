"""Fail-closed loader for canonical compiled graph artifacts."""

from __future__ import annotations

import hashlib
import json
from importlib.resources import files
from pathlib import Path, PurePath, PurePosixPath
from typing import Any

import yaml
from pydantic import ValidationError

from ai_engineering_harness.contracts import (
    CompiledGraphArtifact,
    ContractRegistryError,
    PolicyRegistry,
    PolicyRegistryError,
)
from ai_engineering_harness.versioning import (
    ARTIFACT_SCHEMA_VERSION,
    GRAPH_SCHEMA_VERSION,
    PACKAGE_VERSION,
    POLICY_SCHEMA_VERSION,
)

_PACKAGE_SOURCE_PREFIX = "package://ai_engineering_harness.defaults/"


class ArtifactValidationError(Exception):
    """Base error for an artifact rejected before runtime execution."""


class ArtifactCompatibilityError(ArtifactValidationError):
    """The artifact uses a version namespace that this package cannot execute."""


class ArtifactIntegrityError(ArtifactValidationError):
    """The artifact envelope, digests, or source provenance is inconsistent."""


class MAFAdapter:
    """Load and validate a canonical ``CompiledGraphArtifact`` before runtime."""

    @classmethod
    def load_and_validate(cls, compiled_json_path: Path) -> CompiledGraphArtifact:
        if not compiled_json_path.is_file():
            raise FileNotFoundError(f"compiled graph artifact not found: {compiled_json_path}")
        try:
            artifact_path = compiled_json_path.resolve(strict=True)
            raw_text = artifact_path.read_text(encoding="utf-8")
            raw_artifact = json.loads(raw_text)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ArtifactIntegrityError(f"cannot read compiled graph artifact: {exc}") from exc
        if not isinstance(raw_artifact, dict):
            raise ArtifactIntegrityError("compiled graph artifact must be a JSON object")

        cls._validate_versions(raw_artifact)
        try:
            artifact = CompiledGraphArtifact.model_validate(raw_artifact)
        except (ContractRegistryError, ValidationError, ValueError) as exc:
            raise ArtifactIntegrityError(f"compiled graph artifact is invalid: {exc}") from exc

        if raw_text != artifact.canonical_json():
            raise ArtifactIntegrityError("compiled graph artifact is not canonical JSON")

        project_root = cls._project_root_for(artifact_path)
        try:
            expected_sources = cls._expected_manifest_sources(project_root, artifact)
        except (
            OSError,
            RuntimeError,
            UnicodeError,
            ValueError,
            yaml.YAMLError,
            PolicyRegistryError,
            ValidationError,
        ) as exc:
            raise ArtifactIntegrityError(f"cannot reconstruct source manifest: {exc}") from exc
        observed_sources = {
            (source.source_kind, source.source_id) for source in artifact.source_manifest
        }
        if observed_sources != expected_sources:
            missing = sorted(expected_sources - observed_sources)
            unexpected = sorted(observed_sources - expected_sources)
            raise ArtifactIntegrityError(
                "source_manifest does not exactly match compilation inputs: "
                f"missing={missing}, unexpected={unexpected}"
            )

        for source in artifact.source_manifest:
            try:
                content = cls._read_manifest_source(project_root, source.source_id)
            except (OSError, RuntimeError, UnicodeError) as exc:
                raise ArtifactIntegrityError(
                    f"cannot resolve manifest source {source.source_id!r}: {exc}"
                ) from exc
            observed = f"sha256:{hashlib.sha256(content).hexdigest()}"
            if observed != source.content_digest:
                raise ArtifactIntegrityError(
                    f"manifest source digest mismatch: {source.source_id}"
                )
        return artifact

    @staticmethod
    def _validate_versions(raw_artifact: dict[str, Any]) -> None:
        MAFAdapter._require_exact_version(
            "artifact_schema_version",
            raw_artifact.get("artifact_schema_version"),
            ARTIFACT_SCHEMA_VERSION,
        )
        MAFAdapter._require_exact_version(
            "package_version",
            raw_artifact.get("package_version"),
            PACKAGE_VERSION,
        )

        graph = raw_artifact.get("graph")
        if isinstance(graph, dict):
            metadata = graph.get("graph")
            if isinstance(metadata, dict):
                MAFAdapter._require_exact_version(
                    "graph_schema_version",
                    metadata.get("graph_schema_version"),
                    GRAPH_SCHEMA_VERSION,
                )

        policies = raw_artifact.get("resolved_policies")
        if isinstance(policies, list):
            for index, policy in enumerate(policies):
                if isinstance(policy, dict):
                    MAFAdapter._require_exact_version(
                        f"resolved_policies[{index}].policy_schema_version",
                        policy.get("policy_schema_version"),
                        POLICY_SCHEMA_VERSION,
                    )

    @staticmethod
    def _require_exact_version(name: str, observed: object, expected: str) -> None:
        if observed is not None and observed != expected:
            raise ArtifactCompatibilityError(
                f"{name} must exactly match {expected!r}; observed {observed!r}"
            )

    @staticmethod
    def _project_root_for(artifact_path: Path) -> Path:
        compiled = artifact_path.parent
        state = compiled.parent
        harness = state.parent
        if compiled.name == "compiled" and state.name == "state" and harness.name == ".harness":
            return harness.parent
        return artifact_path.parent

    @staticmethod
    def _read_manifest_source(project_root: Path, source_id: str) -> bytes:
        project_prefix = "project://"
        if source_id.startswith(project_prefix):
            relative = source_id.removeprefix(project_prefix)
            candidate = project_root.joinpath(*relative.split("/"))
            resolved = candidate.resolve(strict=True)
            if not resolved.is_file() or not resolved.is_relative_to(project_root):
                raise OSError("project source escapes the artifact project root")
            content = resolved.read_bytes()
            content.decode("utf-8")
            return content

        if source_id.startswith(_PACKAGE_SOURCE_PREFIX):
            relative = source_id.removeprefix(_PACKAGE_SOURCE_PREFIX)
            resource = files("ai_engineering_harness.defaults").joinpath(*relative.split("/"))
            if not resource.is_file():
                raise OSError("package source is not a regular resource")
            content = resource.read_bytes()
            content.decode("utf-8")
            return content

        raise OSError("unsupported manifest source ID")

    @staticmethod
    def _expected_manifest_sources(
        project_root: Path,
        artifact: CompiledGraphArtifact,
    ) -> set[tuple[str, str]]:
        expected: set[tuple[str, str]] = {
            (source.source_kind, source.source_id)
            for source in artifact.source_manifest
            if source.source_kind == "graph"
        }

        contracts_root = project_root / ".harness" / "contracts"
        for contract in artifact.resolved_contracts:
            if contract.source != "json_schema":
                continue
            raw_path = contract.requested_reference.removeprefix("jsonschema:").partition("#")[0]
            relative = PurePosixPath(raw_path)
            contract_path = contracts_root.joinpath(*relative.parts)
            expected.add(
                (
                    "contract_schema",
                    MAFAdapter._project_source_id(
                        project_root,
                        contract_path,
                        allowed_root=contracts_root,
                    ),
                )
            )

        registry = PolicyRegistry()
        policies_root = project_root / ".harness" / "policies"
        for reference in registry.available_policies:
            project_policy = policies_root / PurePosixPath(reference).name
            project_source = MAFAdapter._optional_project_source_id(
                project_root,
                project_policy,
                allowed_root=policies_root,
            )
            expected.add(
                (
                    "policy",
                    project_source or f"{_PACKAGE_SOURCE_PREFIX}{reference}",
                )
            )

        role_overrides = MAFAdapter._project_role_sources(project_root)
        for role_sources in role_overrides.values():
            expected.update(role_sources)
        for role_id in sorted(set(registry.available_roles) - set(role_overrides)):
            role_path = f"agents/{role_id}/agent.yaml"
            role_document = MAFAdapter._load_package_yaml(role_path)
            prompt_name = MAFAdapter._safe_prompt_name(role_id, role_document)
            expected.update(
                {
                    ("role", f"{_PACKAGE_SOURCE_PREFIX}{role_path}"),
                    (
                        "role_prompt",
                        f"{_PACKAGE_SOURCE_PREFIX}agents/{role_id}/{prompt_name}",
                    ),
                }
            )

        tools_root = project_root / ".harness" / "tools"
        project_tools = MAFAdapter._optional_project_source_id(
            project_root,
            tools_root / "tool_registry.yaml",
            allowed_root=tools_root,
        )
        expected.add(
            (
                "tool_registry",
                project_tools or f"{_PACKAGE_SOURCE_PREFIX}tools/tool_registry.yaml",
            )
        )
        return expected

    @staticmethod
    def _project_role_sources(
        project_root: Path,
    ) -> dict[str, set[tuple[str, str]]]:
        roles_root = project_root / ".harness" / "agents"
        if not roles_root.exists() and not roles_root.is_symlink():
            return {}
        resolved_root = roles_root.resolve(strict=True)
        if not resolved_root.is_dir() or not resolved_root.is_relative_to(project_root):
            raise OSError("agent overrides directory escapes project root")

        sources: dict[str, set[tuple[str, str]]] = {}
        for directory in sorted(resolved_root.iterdir(), key=lambda item: item.name):
            if directory.name.startswith("_") or not directory.is_dir():
                continue
            agent_path = directory / "agent.yaml"
            source_id = MAFAdapter._optional_project_source_id(
                project_root,
                agent_path,
                allowed_root=resolved_root,
            )
            if source_id is None:
                continue
            document = MAFAdapter._load_project_yaml(agent_path)
            prompt_name = MAFAdapter._safe_prompt_name(directory.name, document)
            prompt_id = MAFAdapter._project_source_id(
                project_root,
                directory / prompt_name,
                allowed_root=directory.resolve(strict=True),
            )
            sources[directory.name] = {
                ("role", source_id),
                ("role_prompt", prompt_id),
            }
        return sources

    @staticmethod
    def _optional_project_source_id(
        project_root: Path,
        path: Path,
        *,
        allowed_root: Path,
    ) -> str | None:
        if not path.exists() and not path.is_symlink():
            return None
        return MAFAdapter._project_source_id(
            project_root,
            path,
            allowed_root=allowed_root,
        )

    @staticmethod
    def _project_source_id(
        project_root: Path,
        path: Path,
        *,
        allowed_root: Path,
    ) -> str:
        resolved = path.resolve(strict=True)
        resolved_allowed = allowed_root.resolve(strict=True)
        if (
            not resolved.is_file()
            or not resolved.is_relative_to(resolved_allowed)
            or not resolved.is_relative_to(project_root)
        ):
            raise OSError(f"unsafe project manifest source: {path}")
        return f"project://{resolved.relative_to(project_root).as_posix()}"

    @staticmethod
    def _load_project_yaml(path: Path) -> dict[str, Any]:
        content = path.resolve(strict=True).read_bytes()
        return MAFAdapter._parse_yaml_mapping(content, str(path))

    @staticmethod
    def _load_package_yaml(relative_path: str) -> dict[str, Any]:
        resource = files("ai_engineering_harness.defaults").joinpath(
            *PurePosixPath(relative_path).parts
        )
        if not resource.is_file():
            raise OSError(f"missing package manifest source: {relative_path}")
        return MAFAdapter._parse_yaml_mapping(resource.read_bytes(), relative_path)

    @staticmethod
    def _parse_yaml_mapping(content: bytes, location: str) -> dict[str, Any]:
        loaded = yaml.safe_load(content.decode("utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError(  # noqa: TRY004
                f"manifest YAML source must be an object: {location}"
            )
        return loaded

    @staticmethod
    def _safe_prompt_name(role_id: str, document: dict[str, Any]) -> str:
        prompt_name = document.get("system_prompt_file")
        if (
            not isinstance(prompt_name, str)
            or not prompt_name
            or PurePath(prompt_name).name != prompt_name
        ):
            raise ValueError(f"agent role {role_id!r} has an unsafe system_prompt_file")
        return prompt_name


__all__ = [
    "ArtifactCompatibilityError",
    "ArtifactIntegrityError",
    "ArtifactValidationError",
    "MAFAdapter",
]
