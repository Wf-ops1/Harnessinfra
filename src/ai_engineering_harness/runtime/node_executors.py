"""Typed, fail-closed node executor boundaries for compiled graphs."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Annotated, ClassVar, Protocol, runtime_checkable

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from ai_engineering_harness.contracts import (
    AgentNodeSpec,
    CompiledGraphArtifact,
    DeterministicNodeSpec,
    HumanApprovalNodeSpec,
    NodeSpec,
    TerminalStateSpec,
)
from ai_engineering_harness.contracts.execution import ExecutionId

_NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class NodeExecutorError(Exception):
    """Base class for public node executor failures."""


class NodeExecutorUnavailableError(NodeExecutorError):
    """The selected executor has no operational backend configured."""


class NodeExecutorResultError(NodeExecutorError):
    """A node backend returned a value outside the public result contract."""


class UnsupportedNodeTypeError(NodeExecutorError):
    """No exact executor mapping exists for a node or terminal variant."""


class NodeBackendError(NodeExecutorError):
    """A configured backend failed in a form safe to route through ``on_failure``."""

    def __init__(self, code: str, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")


class NodeExecutionFailure(_StrictFrozenModel):
    """Redaction-safe failure returned by a node backend."""

    code: _NonEmptyStr
    message: _NonEmptyStr
    retryable: bool


class NodeExecutionContext(_StrictFrozenModel):
    """Immutable context supplied to exactly one node backend invocation."""

    execution_id: ExecutionId
    artifact: CompiledGraphArtifact
    node: AgentNodeSpec | DeterministicNodeSpec | HumanApprovalNodeSpec | TerminalStateSpec
    attempt: int = Field(ge=0)
    input_payload: dict[str, object]
    fencing_token: int = Field(gt=0)

    @field_validator("artifact", mode="before")
    @classmethod
    def detach_artifact(cls, value: object) -> CompiledGraphArtifact:
        if not isinstance(value, CompiledGraphArtifact):
            raise TypeError("artifact must be a CompiledGraphArtifact")
        return CompiledGraphArtifact.model_validate_json(value.canonical_json())

    @field_validator("input_payload", mode="before")
    @classmethod
    def detach_input_payload(cls, value: object) -> dict[str, object]:
        return _copy_json_object(value, path="input_payload")


class NodeExecutionResult(_StrictFrozenModel):
    """One backend outcome and the JSON object forwarded to the selected edge."""

    succeeded: bool
    output: dict[str, object]
    failure: NodeExecutionFailure | None = None

    @field_validator("output", mode="before")
    @classmethod
    def detach_output(cls, value: object) -> dict[str, object]:
        return _copy_json_object(value, path="output")

    @model_validator(mode="after")
    def require_matching_failure(self) -> NodeExecutionResult:
        if self.succeeded and self.failure is not None:
            raise ValueError("a successful node result cannot contain failure details")
        if not self.succeeded and self.failure is None:
            raise ValueError("a failed node result requires failure details")
        return self

    @classmethod
    def completed(cls, output: dict[str, object]) -> NodeExecutionResult:
        return cls(succeeded=True, output=output)

    @classmethod
    def failed(
        cls,
        output: dict[str, object],
        *,
        code: str,
        message: str,
        retryable: bool,
    ) -> NodeExecutionResult:
        return cls(
            succeeded=False,
            output=output,
            failure=NodeExecutionFailure(
                code=code,
                message=message,
                retryable=retryable,
            ),
        )


@runtime_checkable
class NodeExecutor(Protocol):
    """Stable executor boundary used by ``GraphExecutor``."""

    def ensure_available(self) -> None:
        """Fail before ``NODE_STARTED`` when the operational backend is unavailable."""

    def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute exactly once and return a typed JSON-native outcome."""


@runtime_checkable
class NodeExecutionBackend(Protocol):
    """Operational backend injected into one effectful node executor."""

    def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Perform the node-specific effect."""


@dataclass(frozen=True, slots=True)
class _BackendNodeExecutor:
    backend: NodeExecutionBackend | None = None
    executor_name: ClassVar[str] = "node"

    def ensure_available(self) -> None:
        if self.backend is None:
            raise NodeExecutorUnavailableError(
                f"{self.executor_name} node executor backend is unavailable"
            )

    def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        self.ensure_available()
        assert self.backend is not None
        try:
            result = self.backend.execute(context)
        except NodeBackendError:
            raise
        except Exception as exc:
            raise NodeBackendError(
                "node_backend_error",
                f"{self.executor_name} node backend failed",
                retryable=False,
            ) from exc
        if not isinstance(result, NodeExecutionResult):
            raise NodeExecutorResultError(
                f"{self.executor_name} node backend returned an invalid result"
            )
        return result


class AgentNodeExecutor(_BackendNodeExecutor):
    """Adapter for an explicitly supplied agent backend."""

    executor_name = "agent"


class DeterministicNodeExecutor(_BackendNodeExecutor):
    """Adapter for an explicitly supplied deterministic backend."""

    executor_name = "deterministic"


class HumanApprovalNodeExecutor(_BackendNodeExecutor):
    """Adapter boundary for human approval without implementing pause/resume."""

    executor_name = "human approval"


class KnowledgeSyncNodeExecutor(_BackendNodeExecutor):
    """Adapter for the existing ``knowledge_updater`` agent role."""

    executor_name = "knowledge sync"


@dataclass(frozen=True, slots=True)
class TerminalNodeExecutor:
    """Resolve an explicit terminal without performing an external effect."""

    def ensure_available(self) -> None:
        return None

    def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        if not isinstance(context.node, TerminalStateSpec):
            raise NodeExecutorResultError(
                "terminal node executor requires a TerminalStateSpec"
            )
        if context.node.outcome == "success":
            return NodeExecutionResult.completed(context.input_payload)
        return NodeExecutionResult.failed(
            context.input_payload,
            code="terminal_failure",
            message="graph reached an explicit failure terminal",
            retryable=False,
        )


@dataclass(frozen=True, slots=True)
class NodeExecutorRegistry:
    """Immutable, exhaustive mapping from graph variants to executors."""

    agent: AgentNodeExecutor = field(default_factory=AgentNodeExecutor)
    deterministic: DeterministicNodeExecutor = field(
        default_factory=DeterministicNodeExecutor
    )
    human_approval: HumanApprovalNodeExecutor = field(
        default_factory=HumanApprovalNodeExecutor
    )
    knowledge_sync: KnowledgeSyncNodeExecutor = field(
        default_factory=KnowledgeSyncNodeExecutor
    )
    terminal: TerminalNodeExecutor = field(default_factory=TerminalNodeExecutor)

    def select(self, node: NodeSpec | TerminalStateSpec) -> NodeExecutor:
        if isinstance(node, AgentNodeSpec):
            if node.role == "knowledge_updater":
                return self.knowledge_sync
            return self.agent
        if isinstance(node, DeterministicNodeSpec):
            return self.deterministic
        if isinstance(node, HumanApprovalNodeSpec):
            return self.human_approval
        if isinstance(node, TerminalStateSpec):
            return self.terminal
        raise UnsupportedNodeTypeError(
            f"unsupported node contract: {type(node).__name__}"
        )


def _copy_json_object(value: object, *, path: str) -> dict[str, object]:
    copied = _copy_json_value(value, path=path)
    if not isinstance(copied, dict):
        raise TypeError(f"{path} must be a JSON object")
    return copied


def _copy_json_value(value: object, *, path: str) -> object:
    if value is None or type(value) in {bool, int, str}:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError(f"{path} contains a non-finite number")
        return value
    if type(value) is list:
        return [
            _copy_json_value(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    if type(value) is dict:
        copied: dict[str, object] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError(f"{path} contains a non-string object key")
            copied[key] = _copy_json_value(item, path=f"{path}.{key}")
        return copied
    raise ValueError(f"{path} contains non-JSON-native value {type(value).__name__}")


__all__ = [
    "AgentNodeExecutor",
    "DeterministicNodeExecutor",
    "HumanApprovalNodeExecutor",
    "KnowledgeSyncNodeExecutor",
    "NodeBackendError",
    "NodeExecutionBackend",
    "NodeExecutionContext",
    "NodeExecutionFailure",
    "NodeExecutionResult",
    "NodeExecutor",
    "NodeExecutorError",
    "NodeExecutorRegistry",
    "NodeExecutorResultError",
    "NodeExecutorUnavailableError",
    "TerminalNodeExecutor",
    "UnsupportedNodeTypeError",
]
