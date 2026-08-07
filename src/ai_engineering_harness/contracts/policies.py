"""Strict F1.3 contracts for packaged policies, roles, tools, and effective views."""

from __future__ import annotations

import json
from typing import Annotated, Any, Literal, Self, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

_NonEmptyStr: TypeAlias = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class PolicyRegistryError(Exception):
    """Base error for fail-closed policy, role, and tool resolution."""


class InvalidPolicyReferenceError(PolicyRegistryError):
    """A policy reference or repeated declaration is invalid."""


class PolicyNotFoundError(PolicyRegistryError):
    """A policy reference has no registered document."""


class InvalidPolicySchemaError(PolicyRegistryError):
    """A policy, role, tool, or effective view violates its strict schema."""


class RoleNotFoundError(PolicyRegistryError):
    """A role is absent or inconsistent with the role catalog."""


class ToolNotFoundError(PolicyRegistryError):
    """A referenced tool capability is absent from the tool registry."""


class UnauthorizedToolError(PolicyRegistryError):
    """A node attempts to exceed or conflict with its role policy."""


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")


def _as_tuple(value: object) -> object:
    return tuple(value) if isinstance(value, list) else value


class ConditionalArtifactSpec(_StrictFrozenModel):
    artifact: _NonEmptyStr
    condition: _NonEmptyStr


class ArtifactManifestSpec(_StrictFrozenModel):
    mandatory: tuple[_NonEmptyStr, ...]
    conditional: tuple[ConditionalArtifactSpec, ...] = ()

    @field_validator("mandatory", "conditional", mode="before")
    @classmethod
    def freeze_sequences(cls, value: object) -> object:
        return _as_tuple(value)


class ContextSufficiencyPolicySpec(_StrictFrozenModel):
    policy_id: _NonEmptyStr
    policy_schema_version: _NonEmptyStr
    definition_version: _NonEmptyStr
    minimum_confidence: float = Field(ge=0.0, le=1.0)
    dual_gate_mode: bool
    required_artifacts_manifest: dict[_NonEmptyStr, ArtifactManifestSpec]
    conflict_handling: _NonEmptyStr
    max_retrieval_retries: int = Field(ge=0)


class AutomationWindowSpec(_StrictFrozenModel):
    max_automated_seconds: int = Field(ge=0)
    escalation_action: _NonEmptyStr


class IncidentResponsePolicySpec(_StrictFrozenModel):
    policy_id: _NonEmptyStr
    policy_schema_version: _NonEmptyStr
    definition_version: _NonEmptyStr
    automation_attempts: dict[_NonEmptyStr, int]
    mttr_policy: dict[_NonEmptyStr, AutomationWindowSpec]
    knowledge_update_requires_incident_resolved: bool
    evidence_retention: _NonEmptyStr

    @field_validator("automation_attempts")
    @classmethod
    def validate_attempts(cls, value: dict[str, int]) -> dict[str, int]:
        if any(attempts < 0 for attempts in value.values()):
            raise ValueError("automation attempts must be non-negative")
        return value


class ChangeDetectionSpec(_StrictFrozenModel):
    root_comparison: _NonEmptyStr
    delta_traversal: _NonEmptyStr


class CommitAssociationSpec(_StrictFrozenModel):
    primary_key: _NonEmptyStr
    metadata_fields: tuple[_NonEmptyStr, ...]
    index_storage_path: _NonEmptyStr
    staging_dir: _NonEmptyStr
    snapshots_dir: _NonEmptyStr
    pointer_file: _NonEmptyStr
    temp_pointer_file: _NonEmptyStr
    lock_file: _NonEmptyStr
    bind_to_execution_id: bool

    @field_validator("metadata_fields", mode="before")
    @classmethod
    def freeze_metadata_fields(cls, value: object) -> object:
        return _as_tuple(value)


class AtomicPointerProtocolSpec(_StrictFrozenModel):
    steps: tuple[dict[_NonEmptyStr, _NonEmptyStr], ...]
    os_portability_note: _NonEmptyStr

    @field_validator("steps", mode="before")
    @classmethod
    def freeze_steps(cls, value: object) -> object:
        return _as_tuple(value)

    @field_validator("steps")
    @classmethod
    def validate_one_action_per_step(
        cls,
        value: tuple[dict[str, str], ...],
    ) -> tuple[dict[str, str], ...]:
        if any(len(step) != 1 for step in value):
            raise ValueError("each durability step must contain exactly one action")
        return value


class SystemInvariantsSpec(_StrictFrozenModel):
    snapshot_exists_rule: _NonEmptyStr
    invalid_pointer_rule: _NonEmptyStr
    no_matching_snapshot_rule: _NonEmptyStr


class ConcurrencyControlSpec(_StrictFrozenModel):
    scope: _NonEmptyStr
    mechanism: _NonEmptyStr
    lock_file: _NonEmptyStr
    lock_metadata: tuple[_NonEmptyStr, ...]
    stale_lock_recovery: _NonEmptyStr

    @field_validator("lock_metadata", mode="before")
    @classmethod
    def freeze_lock_metadata(cls, value: object) -> object:
        return _as_tuple(value)


class RecoveryActionSpec(_StrictFrozenModel):
    action: _NonEmptyStr


class RecoveryRuleSpec(_StrictFrozenModel):
    rule: _NonEmptyStr


class RecoveryStrategiesSpec(_StrictFrozenModel):
    snapshot_missing: RecoveryActionSpec
    merkle_root_mismatch: RecoveryActionSpec
    sqlite_corrupted: RecoveryActionSpec
    commit_mismatch_on_restore: RecoveryRuleSpec
    current_json_corrupted_or_missing: RecoveryActionSpec
    stale_writer_lost_lease: RecoveryActionSpec
    out_of_order_token_writers: RecoveryRuleSpec
    blocked_states_for_agent: tuple[_NonEmptyStr, ...]

    @field_validator("blocked_states_for_agent", mode="before")
    @classmethod
    def freeze_blocked_states(cls, value: object) -> object:
        return _as_tuple(value)


class SlaTargetsSpec(_StrictFrozenModel):
    p50_ms: int = Field(gt=0)
    p95_ms: int = Field(gt=0)
    p99_ms: int = Field(gt=0)


class BenchmarkConditionsSpec(_StrictFrozenModel):
    repo_symbols_limit: int = Field(gt=0)
    cache_state: _NonEmptyStr
    storage_type: _NonEmptyStr


class PerformanceBenchmarkSpec(_StrictFrozenModel):
    sla_targets: SlaTargetsSpec
    benchmark_conditions: BenchmarkConditionsSpec


class GarbageCollectionSpec(_StrictFrozenModel):
    retention_policy: _NonEmptyStr
    orphan_snapshot_action: _NonEmptyStr


class KnowledgeSyncPolicySpec(_StrictFrozenModel):
    policy_id: _NonEmptyStr
    policy_schema_version: _NonEmptyStr
    definition_version: _NonEmptyStr
    sync_mode: _NonEmptyStr
    change_detection: ChangeDetectionSpec
    parsing_engine: _NonEmptyStr
    sync_coordinator_timeout_seconds: int = Field(gt=0)
    partial_sync_action: _NonEmptyStr
    commit_association: CommitAssociationSpec
    atomic_pointer_durability_protocol: AtomicPointerProtocolSpec
    system_invariants: SystemInvariantsSpec
    concurrency_control: ConcurrencyControlSpec
    recovery_strategies: RecoveryStrategiesSpec
    performance_benchmark: PerformanceBenchmarkSpec
    garbage_collection: GarbageCollectionSpec
    context_snapshot_ttl: dict[_NonEmptyStr, _NonEmptyStr]


class SloGateSpec(_StrictFrozenModel):
    slo_id: _NonEmptyStr
    metric: _NonEmptyStr
    baseline_window: _NonEmptyStr
    threshold: _NonEmptyStr


class CanaryStrategySpec(_StrictFrozenModel):
    progression: tuple[int, ...]
    min_step_duration_seconds: int = Field(gt=0)
    min_requests_per_step: int = Field(gt=0)

    @field_validator("progression", mode="before")
    @classmethod
    def freeze_progression(cls, value: object) -> object:
        return _as_tuple(value)


class RollbackTriggerSpec(_StrictFrozenModel):
    any_slo_gate_breached: bool
    rollback_grace_period_seconds: int = Field(ge=0)


class MigrationRollbackSpec(_StrictFrozenModel):
    requires_explicit_strategy: bool
    default_on_missing_strategy: _NonEmptyStr


class ProductionHealthPolicySpec(_StrictFrozenModel):
    policy_id: _NonEmptyStr
    policy_schema_version: _NonEmptyStr
    definition_version: _NonEmptyStr
    observation_window_seconds: int = Field(gt=0)
    evaluation_strategy: _NonEmptyStr
    slo_gates: tuple[SloGateSpec, ...]
    canary_strategy: CanaryStrategySpec
    rollback_trigger: RollbackTriggerSpec
    migration_rollback: MigrationRollbackSpec

    @field_validator("slo_gates", mode="before")
    @classmethod
    def freeze_slo_gates(cls, value: object) -> object:
        return _as_tuple(value)


class ModelRoutingSpec(_StrictFrozenModel):
    retry_0: _NonEmptyStr
    retry_1: _NonEmptyStr
    retry_2: _NonEmptyStr
    retry_max: int = Field(ge=0)


class CostBudgetSpec(_StrictFrozenModel):
    max_tokens_per_node: int = Field(gt=0)
    max_cost_per_execution_usd: float = Field(gt=0)
    escalate_on_budget_exceeded: bool


class RetryCostPolicySpec(_StrictFrozenModel):
    policy_id: _NonEmptyStr
    policy_schema_version: _NonEmptyStr
    definition_version: _NonEmptyStr
    context_strategy: _NonEmptyStr
    semantic_cache_threshold: float = Field(ge=0.0, le=1.0)
    context_deduplication_threshold: float = Field(ge=0.0, le=1.0)
    model_routing: ModelRoutingSpec
    cost_budget: CostBudgetSpec


class IsolationMatrixSpec(_StrictFrozenModel):
    read_analysis: _NonEmptyStr
    code_modification: _NonEmptyStr
    test_execution: _NonEmptyStr
    build_terminal: _NonEmptyStr
    ci_cd_deploy: _NonEmptyStr


class PartialFailureSpec(_StrictFrozenModel):
    action: _NonEmptyStr
    routing: dict[_NonEmptyStr, _NonEmptyStr]


class FanInContractSpec(_StrictFrozenModel):
    merge_strategy: _NonEmptyStr
    conflict_resolution: _NonEmptyStr
    partial_node_failure: PartialFailureSpec


class SandboxPolicySpec(_StrictFrozenModel):
    policy_id: _NonEmptyStr
    policy_schema_version: _NonEmptyStr
    definition_version: _NonEmptyStr
    workspace_scope: _NonEmptyStr
    fan_out_isolation: _NonEmptyStr
    credential_injection: _NonEmptyStr
    lifecycle: _NonEmptyStr
    cold_start_budget_ms: dict[_NonEmptyStr, int]
    isolation_matrix: IsolationMatrixSpec
    fan_in_contract: FanInContractSpec

    @field_validator("cold_start_budget_ms")
    @classmethod
    def validate_cold_start_budgets(cls, value: dict[str, int]) -> dict[str, int]:
        if any(milliseconds <= 0 for milliseconds in value.values()):
            raise ValueError("cold-start budgets must be positive")
        return value


class RoleToolPolicySpec(_StrictFrozenModel):
    allowed_tools: tuple[_NonEmptyStr, ...]
    forbidden_tools: tuple[_NonEmptyStr, ...] = ()
    human_approval_required: bool = False

    @field_validator("allowed_tools", "forbidden_tools", mode="before")
    @classmethod
    def freeze_tools(cls, value: object) -> object:
        return _as_tuple(value)

    @model_validator(mode="after")
    def validate_unique_non_overlapping_tools(self) -> Self:
        if len(set(self.allowed_tools)) != len(self.allowed_tools):
            raise ValueError("allowed_tools must be unique")
        if len(set(self.forbidden_tools)) != len(self.forbidden_tools):
            raise ValueError("forbidden_tools must be unique")
        overlap = sorted(set(self.allowed_tools) & set(self.forbidden_tools))
        if overlap:
            raise ValueError(f"allowed_tools and forbidden_tools overlap: {', '.join(overlap)}")
        return self


class ToolGovernancePolicySpec(_StrictFrozenModel):
    policy_id: _NonEmptyStr
    policy_schema_version: _NonEmptyStr
    definition_version: _NonEmptyStr
    roles_permissions: dict[_NonEmptyStr, RoleToolPolicySpec]


class RequiredGateSpec(_StrictFrozenModel):
    id: _NonEmptyStr
    executor: Literal["deterministic"]
    command: _NonEmptyStr
    blocking: bool


class VerificationPolicySpec(_StrictFrozenModel):
    policy_id: _NonEmptyStr
    policy_schema_version: _NonEmptyStr
    definition_version: _NonEmptyStr
    applies_to: tuple[_NonEmptyStr, ...]
    required_gates: tuple[RequiredGateSpec, ...]
    termination_rule: _NonEmptyStr
    on_failure: _NonEmptyStr

    @field_validator("applies_to", "required_gates", mode="before")
    @classmethod
    def freeze_sequences(cls, value: object) -> object:
        return _as_tuple(value)


PolicyDocument: TypeAlias = (
    ContextSufficiencyPolicySpec
    | IncidentResponsePolicySpec
    | KnowledgeSyncPolicySpec
    | ProductionHealthPolicySpec
    | RetryCostPolicySpec
    | SandboxPolicySpec
    | ToolGovernancePolicySpec
    | VerificationPolicySpec
)


class AgentRoleSpec(_StrictFrozenModel):
    name: _NonEmptyStr
    role: _NonEmptyStr
    inherits: _NonEmptyStr
    model: _NonEmptyStr
    allowed_tools: tuple[_NonEmptyStr, ...]
    system_prompt_file: _NonEmptyStr

    @field_validator("allowed_tools", mode="before")
    @classmethod
    def freeze_allowed_tools(cls, value: object) -> object:
        return _as_tuple(value)

    @model_validator(mode="after")
    def validate_unique_tools(self) -> Self:
        if len(set(self.allowed_tools)) != len(self.allowed_tools):
            raise ValueError("agent allowed_tools must be unique")
        return self


class ToolCapabilitySpec(_StrictFrozenModel):
    id: _NonEmptyStr
    description: _NonEmptyStr
    capability_status: Literal["declared"]


class ToolRegistrySpec(_StrictFrozenModel):
    registry_schema_version: _NonEmptyStr
    definition_version: _NonEmptyStr
    tools: tuple[ToolCapabilitySpec, ...]

    @field_validator("tools", mode="before")
    @classmethod
    def freeze_tools(cls, value: object) -> object:
        return _as_tuple(value)

    @model_validator(mode="after")
    def validate_unique_tool_ids(self) -> Self:
        ids = [tool.id for tool in self.tools]
        if len(set(ids)) != len(ids):
            raise ValueError("tool registry IDs must be unique")
        return self


class EffectiveNodeToolPolicySpec(_StrictFrozenModel):
    node_id: _NonEmptyStr
    role: _NonEmptyStr
    allowed_tools: tuple[_NonEmptyStr, ...] = ()
    denied_tools: tuple[_NonEmptyStr, ...] = ()
    human_approval_required: bool = False

    @field_validator("allowed_tools", "denied_tools", mode="before")
    @classmethod
    def freeze_tools(cls, value: object) -> object:
        return _as_tuple(value)


def _detached_json_object(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InvalidPolicySchemaError("effective policy must be a JSON object")
    try:
        detached = json.loads(
            json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True)
        )
    except (TypeError, ValueError) as exc:
        raise InvalidPolicySchemaError(f"effective policy is not canonical JSON: {exc}") from exc
    if not isinstance(detached, dict):
        raise InvalidPolicySchemaError("effective policy must normalize to a JSON object")
    return detached


class ResolvedPolicySpec(_StrictFrozenModel):
    """A normalized effective policy view safe to embed in a compiled artifact."""

    requested_reference: _NonEmptyStr
    policy_id: _NonEmptyStr
    policy_schema_version: _NonEmptyStr
    definition_version: _NonEmptyStr
    effective_policy: dict[str, Any]

    @field_validator("effective_policy", mode="before")
    @classmethod
    def detach_effective_policy(cls, value: object) -> dict[str, Any]:
        return _detached_json_object(value)


__all__ = [
    "AgentRoleSpec",
    "ContextSufficiencyPolicySpec",
    "EffectiveNodeToolPolicySpec",
    "IncidentResponsePolicySpec",
    "InvalidPolicyReferenceError",
    "InvalidPolicySchemaError",
    "KnowledgeSyncPolicySpec",
    "PolicyDocument",
    "PolicyNotFoundError",
    "PolicyRegistryError",
    "ProductionHealthPolicySpec",
    "ResolvedPolicySpec",
    "RetryCostPolicySpec",
    "RoleNotFoundError",
    "RoleToolPolicySpec",
    "SandboxPolicySpec",
    "ToolCapabilitySpec",
    "ToolGovernancePolicySpec",
    "ToolNotFoundError",
    "ToolRegistrySpec",
    "UnauthorizedToolError",
    "VerificationPolicySpec",
]
