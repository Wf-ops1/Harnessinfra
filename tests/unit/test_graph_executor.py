"""Focused F2.3 tests for canonical graph traversal and fail-closed boundaries."""

from __future__ import annotations

import hashlib
import json
import multiprocessing
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from queue import Empty

import pytest

from ai_engineering_harness.contracts import (
    AgentNodeSpec,
    CompiledGraphArtifact,
    DeterministicNodeSpec,
    GraphSpec,
    HumanApprovalNodeSpec,
    ResolvedContractSpec,
    SourceManifestEntry,
    TerminalStateSpec,
)
from ai_engineering_harness.contracts.events import ExecutionEvent
from ai_engineering_harness.contracts.execution import (
    ApprovalStatus,
    ExecutionRecord,
    ExecutionState,
)
from ai_engineering_harness.persistence import (
    AtomicFileStateStorage,
    EventJournalStateStorageProvider,
    ExecutionLock,
    StateStorageProvider,
    StateWriteError,
)
from ai_engineering_harness.runtime import (
    AgentNodeExecutor,
    ArtifactExecutionMismatchError,
    DeterministicNodeExecutor,
    GraphCycleExecutionError,
    GraphExecutor,
    HumanApprovalNodeExecutor,
    InterruptedExecutionError,
    KnowledgeSyncNodeExecutor,
    NodeBackendError,
    NodeExecutionContext,
    NodeExecutionResult,
    NodeExecutorRegistry,
    NodeExecutorUnavailableError,
    NodeInputValidationError,
    StateReplayError,
    StateTransitionIntegrityError,
    TerminalNodeExecutor,
    UnknownCurrentNodeError,
)

_BASE_TIME = datetime(2020, 1, 1, 0, 0, tzinfo=UTC)
_ZERO_DIGEST = f"sha256:{'0' * 64}"


class _Clock:
    def __init__(self) -> None:
        self.value = _BASE_TIME

    def __call__(self) -> datetime:
        self.value += timedelta(seconds=1)
        return self.value


class _EventIds:
    def __init__(self) -> None:
        self.value = 0

    def __call__(self) -> str:
        self.value += 1
        return f"event-{self.value}"


@dataclass
class _TraceBackend:
    trace: list[str]
    fail_node: str | None = None
    invalid_output_node: str | None = None
    raise_node: str | None = None

    def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        node_id = context.node.id
        self.trace.append(node_id)
        if node_id == self.raise_node:
            raise NodeBackendError(
                "backend_rejected",
                "backend rejected the node",
                retryable=False,
            )
        if node_id == self.invalid_output_node:
            return NodeExecutionResult.completed({"result": 42})
        previous = context.input_payload.get("trace", [])
        assert isinstance(previous, list)
        output = {"trace": [*previous, node_id]}
        if node_id == self.fail_node:
            return NodeExecutionResult.failed(
                output,
                code="controlled_failure",
                message="controlled node failure",
                retryable=False,
            )
        return NodeExecutionResult.completed(output)


@dataclass
class _MarkerBackend:
    marker: Path

    def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        with self.marker.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(f"{context.node.id}\n")
            stream.flush()
        return NodeExecutionResult.completed({"worker": context.node.id})


@dataclass
class _StaticBackend:
    result: object

    def execute(self, context: NodeExecutionContext) -> object:
        return self.result


class _FailingStorage:
    def __init__(
        self,
        inner: AtomicFileStateStorage,
        *,
        fail_append_number: int | None = None,
        fail_cas: bool = False,
    ) -> None:
        self.inner = inner
        self.fail_append_number = fail_append_number
        self.fail_cas = fail_cas
        self.append_count = 0

    def create_execution(self, record: ExecutionRecord) -> ExecutionRecord:
        return self.inner.create_execution(record)

    def load_execution(
        self,
        execution_id: str,
        *,
        lock: ExecutionLock | None = None,
    ) -> ExecutionRecord:
        return self.inner.load_execution(execution_id, lock=lock)

    def compare_and_set_execution(
        self,
        execution_id: str,
        expected_revision: int,
        replacement: ExecutionRecord,
        *,
        lock: ExecutionLock | None = None,
    ) -> ExecutionRecord:
        if self.fail_cas:
            raise StateWriteError("controlled CAS failure", execution_id=execution_id)
        return self.inner.compare_and_set_execution(
            execution_id,
            expected_revision,
            replacement,
            lock=lock,
        )

    def append_event(
        self,
        execution_id: str,
        event: ExecutionEvent,
        *,
        lock: ExecutionLock | None = None,
    ) -> ExecutionEvent:
        self.append_count += 1
        if self.append_count == self.fail_append_number:
            raise StateWriteError("controlled append failure", execution_id=execution_id)
        return self.inner.append_event(execution_id, event, lock=lock)

    def load_events(
        self,
        execution_id: str,
        *,
        lock: ExecutionLock | None = None,
    ) -> tuple[ExecutionEvent, ...]:
        return self.inner.load_events(execution_id, lock=lock)

    def list_executions(self) -> tuple[ExecutionRecord, ...]:
        return self.inner.list_executions()

    def acquire_execution_lock(
        self,
        execution_id: str,
        owner_id: str,
        *,
        timeout_seconds: float,
    ) -> ExecutionLock:
        return self.inner.acquire_execution_lock(
            execution_id,
            owner_id,
            timeout_seconds=timeout_seconds,
        )

    def release_execution_lock(self, lock: ExecutionLock) -> None:
        self.inner.release_execution_lock(lock)


def _artifact(
    nodes: list[dict[str, object]],
    *,
    name: str = "test-graph",
    entrypoint: str | None = None,
    contracts: tuple[ResolvedContractSpec, ...] = (),
) -> CompiledGraphArtifact:
    graph = GraphSpec.model_validate(
        {
            "graph": {
                "name": name,
                "graph_schema_version": "1.0",
                "definition_version": "1.0.0",
                "entrypoint": entrypoint or str(nodes[0]["id"]),
                "status": "stable",
            },
            "nodes": nodes,
            "terminal_states": [
                {"id": "completed", "outcome": "success"},
                {"id": "failed", "outcome": "failure"},
            ],
            "policies": [],
            "contracts": [],
        }
    )
    return CompiledGraphArtifact.build(
        graph=graph,
        resolved_contracts=contracts,
        resolved_policies=(),
        source_manifest=(
            SourceManifestEntry(
                source_kind="graph",
                source_id="project://graph.yaml",
                content_digest=_ZERO_DIGEST,
            ),
        ),
    )


def _deterministic_node(
    node_id: str,
    on_success: str,
    *,
    on_failure: str = "failed",
    retry_policy: dict[str, object] | None = None,
) -> dict[str, object]:
    node: dict[str, object] = {
        "id": node_id,
        "type": "deterministic",
        "executor": "deterministic_gate",
        "gate_name": node_id,
        "on_success": on_success,
        "on_failure": on_failure,
    }
    if retry_policy is not None:
        node["retry_policy"] = retry_policy
    return node


def _resolved_contract(reference: str, schema: dict[str, object]) -> ResolvedContractSpec:
    canonical = json.dumps(
        schema,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return ResolvedContractSpec(
        canonical_name=reference,
        requested_reference=reference,
        source="json_schema",
        contract_schema=schema,
        digest=f"sha256:{hashlib.sha256(canonical).hexdigest()}",
    )


def _agent_artifact() -> CompiledGraphArtifact:
    input_ref = "jsonschema:input.json"
    output_ref = "jsonschema:output.json"
    return _artifact(
        [
            {
                "id": "agent",
                "type": "agent",
                "role": "code_agent",
                "input_contract": input_ref,
                "output_contract": output_ref,
                "on_success": "completed",
                "on_failure": "failed",
            }
        ],
        contracts=(
            _resolved_contract(
                input_ref,
                {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "type": "object",
                    "properties": {"value": {"type": "integer"}},
                    "required": ["value"],
                    "additionalProperties": False,
                },
            ),
            _resolved_contract(
                output_ref,
                {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "type": "object",
                    "properties": {"result": {"type": "string"}},
                    "required": ["result"],
                    "additionalProperties": False,
                },
            ),
        ),
    )


def _record(
    artifact: CompiledGraphArtifact,
    execution_id: str,
    *,
    current_node_id: str | None = None,
    artifact_digest: str | None = None,
) -> ExecutionRecord:
    digest = artifact_digest or (
        "sha256:"
        + hashlib.sha256(artifact.canonical_json().encode("utf-8")).hexdigest()
    )
    return ExecutionRecord(
        record_schema_version="1.0",
        revision=0,
        execution_id=execution_id,
        workflow_name=artifact.graph.graph.name,
        artifact_digest=digest,
        base_commit_sha="a" * 40,
        original_branch="test",
        worktree_path=None,
        current_node_id=current_node_id or artifact.graph.graph.entrypoint,
        current_state=ExecutionState.INITIATED,
        attempt_by_node={},
        created_at=_BASE_TIME,
        updated_at=_BASE_TIME,
        configuration_digest=_ZERO_DIGEST,
        approval_status=ApprovalStatus.NOT_REQUIRED,
        candidate_commit_sha=None,
        promotion_commit_sha=None,
        failure=None,
    )


def _executor(
    storage: EventJournalStateStorageProvider,
    registry: NodeExecutorRegistry,
) -> GraphExecutor:
    return GraphExecutor(
        storage,
        registry,
        lock_timeout_seconds=5,
        clock=_Clock(),
        event_id_factory=_EventIds(),
        owner_id_factory=lambda: "unit-test-worker",
    )


def _journal(root: Path, execution_id: str) -> list[dict[str, object]]:
    path = (
        root
        / ".harness"
        / "state"
        / "executions"
        / execution_id
        / "event-journal.jsonl"
    )
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _multiprocess_execute(
    project_root: str,
    artifact_json: str,
    execution_id: str,
    marker: str,
    start_event: object,
    result_queue: object,
) -> None:
    start_event.wait(10)
    artifact = CompiledGraphArtifact.model_validate_json(artifact_json)
    storage = AtomicFileStateStorage(Path(project_root))
    backend = _MarkerBackend(Path(marker))
    executor = GraphExecutor(
        storage,
        NodeExecutorRegistry(
            deterministic=DeterministicNodeExecutor(backend),
        ),
        lock_timeout_seconds=10,
    )
    result = executor.execute(artifact, execution_id, {"worker": "ready"})
    result_queue.put(("ok", result.executed_node_ids, result.fencing_token))


def test_dispatch_selects_all_five_executor_variants() -> None:
    registry = NodeExecutorRegistry()
    agent = AgentNodeSpec(
        id="agent",
        type="agent",
        role="code_agent",
        input_contract="Input",
        output_contract="Output",
        on_success="completed",
        on_failure="failed",
    )
    knowledge = agent.model_copy(update={"id": "knowledge", "role": "knowledge_updater"})
    deterministic = DeterministicNodeSpec(
        id="gate",
        type="deterministic",
        executor="deterministic_gate",
        gate_name="quality",
        on_success="completed",
        on_failure="failed",
    )
    approval = HumanApprovalNodeSpec(
        id="approval",
        type="human_approval",
        approval_strategy="explicit",
        on_success="completed",
        on_failure="failed",
    )
    terminal = TerminalStateSpec(id="completed", outcome="success")

    assert isinstance(registry.select(agent), AgentNodeExecutor)
    assert isinstance(registry.select(knowledge), KnowledgeSyncNodeExecutor)
    assert isinstance(registry.select(deterministic), DeterministicNodeExecutor)
    assert isinstance(registry.select(approval), HumanApprovalNodeExecutor)
    assert isinstance(registry.select(terminal), TerminalNodeExecutor)


def test_linear_execution_persists_events_cas_terminal_and_fencing(tmp_path: Path) -> None:
    artifact = _artifact(
        [
            _deterministic_node("first", "second"),
            _deterministic_node("second", "completed"),
        ]
    )
    storage = AtomicFileStateStorage(tmp_path)
    storage.create_execution(_record(artifact, "exec-linear"))
    trace: list[str] = []
    result = _executor(
        storage,
        NodeExecutorRegistry(
            deterministic=DeterministicNodeExecutor(_TraceBackend(trace)),
        ),
    ).execute(artifact, "exec-linear", {"trace": []})

    assert trace == ["first", "second"]
    assert result.outcome == "success"
    assert result.terminal_id == "completed"
    assert result.executed_node_ids == ("first", "second")
    assert result.final_revision == 4
    assert result.output == {"trace": ["first", "second"]}
    persisted = storage.load_execution("exec-linear")
    assert persisted.current_node_id == "completed"
    assert persisted.revision == 4
    assert persisted.current_state == ExecutionState.COMPLETED
    assert persisted.attempt_by_node == {"first": 1, "second": 1}
    events = _journal(tmp_path, "exec-linear")
    assert [event["event_type"] for event in events] == [
        "STATE_TRANSITIONED",
        "NODE_STARTED",
        "NODE_COMPLETED",
        "NODE_STARTED",
        "NODE_COMPLETED",
        "STATE_TRANSITIONED",
    ]
    assert all(event["payload"]["fencing_token"] == result.fencing_token for event in events)
    assert [event["payload"].get("next_id") for event in events[1:-1]] == [
        None,
        "second",
        None,
        "completed",
    ]
    assert events[0]["payload"]["to_state"] == "EXECUTING"
    assert events[-1]["payload"]["to_state"] == "COMPLETED"


def test_valid_input_contract_and_output_contract_complete(tmp_path: Path) -> None:
    artifact = _agent_artifact()
    storage = AtomicFileStateStorage(tmp_path)
    storage.create_execution(_record(artifact, "exec-valid-contracts"))
    result = _executor(
        storage,
        NodeExecutorRegistry(
            agent=AgentNodeExecutor(
                _StaticBackend(NodeExecutionResult.completed({"result": "ok"}))
            )
        ),
    ).execute(artifact, "exec-valid-contracts", {"value": 1})

    assert result.outcome == "success"
    assert result.output == {"result": "ok"}
    assert [event["event_type"] for event in _journal(tmp_path, "exec-valid-contracts")] == [
        "STATE_TRANSITIONED",
        "NODE_STARTED",
        "NODE_COMPLETED",
        "STATE_TRANSITIONED",
    ]


def test_invalid_input_contract_rejection_is_side_effect_free(tmp_path: Path) -> None:
    artifact = _agent_artifact()
    storage = AtomicFileStateStorage(tmp_path)
    storage.create_execution(_record(artifact, "exec-invalid-input"))
    trace: list[str] = []
    executor = _executor(
        storage,
        NodeExecutorRegistry(agent=AgentNodeExecutor(_TraceBackend(trace))),
    )

    with pytest.raises(NodeInputValidationError):
        executor.execute(artifact, "exec-invalid-input", {"value": "not-an-int"})

    assert trace == []
    assert _journal(tmp_path, "exec-invalid-input") == []
    assert storage.load_execution("exec-invalid-input").revision == 0


def test_invalid_output_follows_failure_edge(tmp_path: Path) -> None:
    artifact = _agent_artifact()
    storage = AtomicFileStateStorage(tmp_path)
    storage.create_execution(_record(artifact, "exec-invalid-output"))
    trace: list[str] = []
    result = _executor(
        storage,
        NodeExecutorRegistry(
            agent=AgentNodeExecutor(
                _TraceBackend(trace, invalid_output_node="agent")
            )
        ),
    ).execute(artifact, "exec-invalid-output", {"value": 1})

    assert result.outcome == "failure"
    assert result.terminal_id == "failed"
    assert result.failure is not None
    assert result.failure.code == "invalid_node_output"
    assert storage.load_execution("exec-invalid-output").current_node_id == "failed"
    events = _journal(tmp_path, "exec-invalid-output")
    assert [event["event_type"] for event in events] == [
        "STATE_TRANSITIONED",
        "NODE_STARTED",
        "NODE_FAILED",
        "STATE_TRANSITIONED",
    ]
    assert events[-2]["payload"]["error_code"] == "invalid_node_output"
    assert events[-1]["payload"]["to_state"] == "FAILED"


def test_backend_failure_follows_only_failure_edge(tmp_path: Path) -> None:
    artifact = _artifact([_deterministic_node("gate", "completed")])
    storage = AtomicFileStateStorage(tmp_path)
    storage.create_execution(_record(artifact, "exec-backend-failure"))
    result = _executor(
        storage,
        NodeExecutorRegistry(
            deterministic=DeterministicNodeExecutor(
                _TraceBackend([], raise_node="gate")
            )
        ),
    ).execute(artifact, "exec-backend-failure", {})

    assert result.outcome == "failure"
    assert result.failure is not None
    assert result.failure.code == "backend_rejected"
    assert storage.load_execution("exec-backend-failure").current_node_id == "failed"


def test_malformed_backend_result_follows_failure_edge(tmp_path: Path) -> None:
    artifact = _artifact([_deterministic_node("gate", "completed")])
    storage = AtomicFileStateStorage(tmp_path)
    storage.create_execution(_record(artifact, "exec-malformed"))
    result = _executor(
        storage,
        NodeExecutorRegistry(
            deterministic=DeterministicNodeExecutor(_StaticBackend({"not": "typed"})),
        ),
    ).execute(artifact, "exec-malformed", {})

    assert result.outcome == "failure"
    assert result.failure is not None
    assert result.failure.code == "invalid_node_result"
    assert _journal(tmp_path, "exec-malformed")[-2]["event_type"] == "NODE_FAILED"


def test_invalid_event_id_prevents_backend_and_cas(tmp_path: Path) -> None:
    artifact = _artifact([_deterministic_node("gate", "completed")])
    storage = AtomicFileStateStorage(tmp_path)
    storage.create_execution(_record(artifact, "exec-invalid-event"))
    trace: list[str] = []
    executor = GraphExecutor(
        storage,
        NodeExecutorRegistry(
            deterministic=DeterministicNodeExecutor(_TraceBackend(trace)),
        ),
        clock=_Clock(),
        event_id_factory=lambda: "invalid event id",
        owner_id_factory=lambda: "unit-test-worker",
    )

    with pytest.raises(StateTransitionIntegrityError):
        executor.execute(artifact, "exec-invalid-event", {})

    assert trace == []
    assert storage.load_execution("exec-invalid-event").revision == 0
    assert _journal(tmp_path, "exec-invalid-event") == []


@pytest.mark.parametrize(
    ("case", "record_kwargs", "error_type"),
    [
        ("unknown", {"current_node_id": "missing"}, UnknownCurrentNodeError),
        (
            "mismatch",
            {"artifact_digest": f"sha256:{'f' * 64}"},
            ArtifactExecutionMismatchError,
        ),
    ],
)
def test_unknown_or_artifact_mismatch_is_side_effect_free(
    tmp_path: Path,
    case: str,
    record_kwargs: dict[str, str],
    error_type: type[Exception],
) -> None:
    artifact = _artifact([_deterministic_node("gate", "completed")])
    execution_id = f"exec-{case}"
    storage = AtomicFileStateStorage(tmp_path)
    storage.create_execution(_record(artifact, execution_id, **record_kwargs))
    executor = _executor(
        storage,
        NodeExecutorRegistry(
            deterministic=DeterministicNodeExecutor(_TraceBackend([])),
        ),
    )

    with pytest.raises(error_type):
        executor.execute(artifact, execution_id, {})

    assert _journal(tmp_path, execution_id) == []
    assert storage.load_execution(execution_id).revision == 0


def test_unavailable_executor_is_side_effect_free(tmp_path: Path) -> None:
    artifact = _artifact([_deterministic_node("gate", "completed")])
    storage = AtomicFileStateStorage(tmp_path)
    storage.create_execution(_record(artifact, "exec-unavailable"))

    with pytest.raises(NodeExecutorUnavailableError):
        _executor(storage, NodeExecutorRegistry()).execute(
            artifact,
            "exec-unavailable",
            {},
        )

    assert _journal(tmp_path, "exec-unavailable") == []
    assert storage.load_execution("exec-unavailable").revision == 0


def test_cycle_revisit_is_rejected_before_second_execution(tmp_path: Path) -> None:
    artifact = _artifact(
        [
            _deterministic_node(
                "loop",
                "loop",
                retry_policy={"max_iterations": 2, "exit_condition": "later"},
            )
        ]
    )
    storage = AtomicFileStateStorage(tmp_path)
    storage.create_execution(_record(artifact, "exec-cycle"))
    trace: list[str] = []
    executor = _executor(
        storage,
        NodeExecutorRegistry(
            deterministic=DeterministicNodeExecutor(_TraceBackend(trace)),
        ),
    )

    with pytest.raises(GraphCycleExecutionError):
        executor.execute(artifact, "exec-cycle", {"trace": []})

    assert trace == ["loop"]
    assert storage.load_execution("exec-cycle").revision == 2
    assert len(_journal(tmp_path, "exec-cycle")) == 3


def test_append_failure_prevents_backend_and_cas(tmp_path: Path) -> None:
    artifact = _artifact([_deterministic_node("gate", "completed")])
    inner = AtomicFileStateStorage(tmp_path)
    inner.create_execution(_record(artifact, "exec-append-failure"))
    storage = _FailingStorage(inner, fail_append_number=1)
    assert isinstance(storage, StateStorageProvider)
    assert isinstance(storage, EventJournalStateStorageProvider)
    trace: list[str] = []

    with pytest.raises(StateWriteError):
        _executor(
            storage,
            NodeExecutorRegistry(
                deterministic=DeterministicNodeExecutor(_TraceBackend(trace)),
            ),
        ).execute(artifact, "exec-append-failure", {})

    assert trace == []
    assert inner.load_execution("exec-append-failure").revision == 0
    assert _journal(tmp_path, "exec-append-failure") == []


def test_cas_failure_is_not_masked_and_preserves_events(tmp_path: Path) -> None:
    artifact = _artifact([_deterministic_node("gate", "completed")])
    inner = AtomicFileStateStorage(tmp_path)
    inner.create_execution(_record(artifact, "exec-cas-failure"))
    storage = _FailingStorage(inner, fail_cas=True)

    with pytest.raises(StateWriteError):
        _executor(
            storage,
            NodeExecutorRegistry(
                deterministic=DeterministicNodeExecutor(_TraceBackend([])),
            ),
        ).execute(artifact, "exec-cas-failure", {})

    assert inner.load_execution("exec-cas-failure").revision == 0
    assert [event["event_type"] for event in _journal(tmp_path, "exec-cas-failure")] == [
        "STATE_TRANSITIONED",
    ]


def test_terminal_worker_does_not_reexecute_node(tmp_path: Path) -> None:
    artifact = _artifact([_deterministic_node("gate", "completed")])
    storage = AtomicFileStateStorage(tmp_path)
    storage.create_execution(_record(artifact, "exec-terminal-worker"))
    trace: list[str] = []
    executor = _executor(
        storage,
        NodeExecutorRegistry(
            deterministic=DeterministicNodeExecutor(_TraceBackend(trace)),
        ),
    )
    first = executor.execute(artifact, "exec-terminal-worker", {})
    journal_before = _journal(tmp_path, "exec-terminal-worker")
    result = executor.execute(
        artifact,
        "exec-terminal-worker",
        {"preserved": True},
    )

    assert first.executed_node_ids == ("gate",)
    assert result.outcome == "success"
    assert result.executed_node_ids == ()
    assert result.final_revision == 3
    assert trace == ["gate"]
    assert _journal(tmp_path, "exec-terminal-worker") == journal_before


def test_terminal_snapshot_mismatch_is_side_effect_free(tmp_path: Path) -> None:
    artifact = _artifact([_deterministic_node("gate", "completed")])
    execution_id = "exec-terminal-mismatch"
    storage = AtomicFileStateStorage(tmp_path)
    storage.create_execution(
        _record(artifact, execution_id, current_node_id="completed")
    )

    with pytest.raises(StateReplayError, match="terminal node"):
        _executor(storage, NodeExecutorRegistry()).execute(
            artifact,
            execution_id,
            {},
        )

    assert storage.load_execution(execution_id).revision == 0
    assert _journal(tmp_path, execution_id) == []


def test_interrupted_execution_does_not_reexecute_backend(tmp_path: Path) -> None:
    artifact = _artifact(
        [
            _deterministic_node(
                "loop",
                "loop",
                retry_policy={"max_iterations": 2, "exit_condition": "later"},
            )
        ]
    )
    storage = AtomicFileStateStorage(tmp_path)
    storage.create_execution(_record(artifact, "exec-interrupted"))
    trace: list[str] = []
    executor = _executor(
        storage,
        NodeExecutorRegistry(
            deterministic=DeterministicNodeExecutor(_TraceBackend(trace)),
        ),
    )
    with pytest.raises(GraphCycleExecutionError):
        executor.execute(artifact, "exec-interrupted", {})
    journal_before = _journal(tmp_path, "exec-interrupted")

    with pytest.raises(InterruptedExecutionError):
        executor.execute(artifact, "exec-interrupted", {})

    assert trace == ["loop"]
    assert _journal(tmp_path, "exec-interrupted") == journal_before


def test_concurrent_workers_do_not_duplicate_effect(tmp_path: Path) -> None:
    artifact = _artifact([_deterministic_node("gate", "completed")])
    execution_id = "exec-concurrent"
    storage = AtomicFileStateStorage(tmp_path)
    storage.create_execution(_record(artifact, execution_id))
    marker = tmp_path / "effects.txt"
    context = multiprocessing.get_context("spawn")
    start_event = context.Event()
    result_queue = context.Queue()
    processes = [
        context.Process(
            target=_multiprocess_execute,
            args=(
                str(tmp_path),
                artifact.canonical_json(),
                execution_id,
                str(marker),
                start_event,
                result_queue,
            ),
        )
        for _ in range(2)
    ]
    for process in processes:
        process.start()
    start_event.set()
    for process in processes:
        process.join(20)
        assert process.exitcode == 0

    try:
        results = [result_queue.get(timeout=5) for _ in processes]
    except Empty as exc:
        pytest.fail(f"worker did not report a result: {exc}")
    assert all(result[0] == "ok" for result in results), results
    assert sorted(result[1] for result in results) == [(), ("gate",)]
    assert len({result[2] for result in results}) == 2
    assert marker.read_text(encoding="utf-8").splitlines() == ["gate"]
    persisted = storage.load_execution(execution_id)
    assert persisted.revision == 3
    assert persisted.current_state == ExecutionState.COMPLETED
