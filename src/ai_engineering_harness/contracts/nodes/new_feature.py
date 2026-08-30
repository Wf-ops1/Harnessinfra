"""Stable state contract carried by the public ``new-feature`` workflow."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

_NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
_RequirementId = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$"),
]


class NewFeatureExecutionState(BaseModel):
    """Immutable JSON state shared by the operational feature nodes."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    requirement_id: _RequirementId
    intent: _NonEmptyStr
    affected_files: tuple[_NonEmptyStr, ...] = ()
    acceptance_criteria: tuple[_NonEmptyStr, ...] = ()
    modified_files: tuple[_NonEmptyStr, ...] = ()
    summary: _NonEmptyStr | None = None
    knowledge_status: Literal["PENDING", "COMMITTED"] = "PENDING"

    @field_validator(
        "affected_files",
        "acceptance_criteria",
        "modified_files",
        mode="before",
    )
    @classmethod
    def freeze_sequences(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value

    @field_validator("affected_files", "modified_files")
    @classmethod
    def require_unique_paths(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value):
            raise ValueError("feature paths must be unique")
        for raw_path in value:
            path = PurePosixPath(raw_path)
            if (
                path.is_absolute()
                or "\\" in raw_path
                or ":" in raw_path
                or "://" in raw_path
                or any(part in {"", ".", ".."} for part in raw_path.split("/"))
                or path.as_posix() != raw_path
            ):
                raise ValueError("feature paths must be normalized POSIX relative paths")
        return value

    @field_validator("acceptance_criteria")
    @classmethod
    def require_unique_criteria(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value):
            raise ValueError("acceptance criteria must be unique")
        return value


__all__ = ["NewFeatureExecutionState"]
