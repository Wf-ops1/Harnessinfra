"""F7.C1 product proof through only the installed public CLI composition."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Self

ROOT = Path(__file__).resolve().parents[2]

_BASE_APPLICATION = '''"""Small application changed through the public workflow."""


def feature_status() -> str:
    return "baseline-ready"
'''

_BASE_TEST = '''from demo_app.core import feature_status


def test_feature_status_is_ready() -> None:
    assert feature_status() == "public-ready"
'''

_PROJECT_TOML = '''[project]
name = "f7c1-public-product"
version = "0.1.0"
requires-python = ">=3.11"

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-p no:cacheprovider"
pythonpath = ["."]

[tool.mypy]
strict = true
exclude = ['^\\.harness/']

[tool.ruff]
exclude = [".harness"]
'''

_GITIGNORE = '''.harness/artifacts/
.harness/state/
.mypy_cache/
.pytest_cache/
.ruff_cache/
__pycache__/
*.pyc
'''

_VERIFICATION_POLICY = '''policy_id: f7c1-public-verification
policy_schema_version: "1.0"
definition_version: "7.4.1"
applies_to:
  - new-feature
required_gates:
  - id: typecheck
    executor: deterministic
    command: "python -m mypy demo_app tests"
    blocking: true
  - id: lint
    executor: deterministic
    command: "python -m ruff check demo_app tests"
    blocking: true
  - id: unit_test
    executor: deterministic
    command: "python -m pytest --maxfail=1 -p no:cacheprovider"
    blocking: true
termination_rule: ALL_REQUIRED_GATES_PASSED
on_failure: route_to_failure_classifier
'''


def _run(
    argv: list[str],
    *,
    cwd: Path,
    environment: dict[str, str] | None = None,
    timeout: float = 240.0,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        argv,
        cwd=cwd,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        shell=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"command failed: {argv!r}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def _git(repository: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return _run(["git", *args], cwd=repository)


def _uv_executable() -> str:
    configured = os.environ.get("HARNESS_TEST_UV")
    if configured:
        candidate = Path(configured)
        assert candidate.is_file(), configured
        return str(candidate)
    discovered = shutil.which("uv")
    assert discovered is not None, "F7.C1 requires uv on PATH or HARNESS_TEST_UV"
    return discovered


def _build_and_install_wheel(
    *,
    distribution: Path,
    installed_environment: Path,
    command_environment: dict[str, str],
) -> Path:
    build_python = os.environ.get("HARNESS_TEST_BUILD_PYTHON")
    if build_python:
        builder = Path(build_python)
        assert builder.is_file(), build_python
        _run(
            [
                str(builder),
                "-m",
                "pip",
                "wheel",
                ".",
                "--no-build-isolation",
                "--no-deps",
                "--wheel-dir",
                str(distribution),
            ],
            cwd=ROOT,
            environment=command_environment,
        )
    else:
        uv = _uv_executable()
        _run(
            [uv, "build", "--wheel", "--offline", "--out-dir", str(distribution)],
            cwd=ROOT,
            environment=command_environment,
        )
    wheels = tuple(distribution.glob("*.whl"))
    assert len(wheels) == 1
    wheel = wheels[0]
    if build_python:
        _run(
            [
                build_python,
                "-m",
                "pip",
                "install",
                "--no-index",
                "--target",
                str(installed_environment),
                "--no-deps",
                str(wheel),
            ],
            cwd=distribution,
            environment=command_environment,
        )
    else:
        uv = _uv_executable()
        _run(
            [
                uv,
                "pip",
                "install",
                "--offline",
                "--target",
                str(installed_environment),
                "--no-deps",
                str(wheel),
            ],
            cwd=distribution,
            environment=command_environment,
        )
    return wheel


def _chat_response(
    *,
    request_number: int,
    content: str = "",
    tool_calls: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    message: dict[str, object] = {"role": "assistant", "content": content or None}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return {
        "id": f"f7c1-response-{request_number}",
        "object": "chat.completion",
        "model": "f7c1-controlled-local",
        "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
        "usage": {
            "prompt_tokens": 7,
            "completion_tokens": 5,
            "total_tokens": 12,
        },
    }


class _ControlledModelServer:
    def __init__(self, *, expected_sha256: str) -> None:
        self.expected_sha256 = expected_sha256
        self.request_kinds: list[str] = []
        self.tool_names: tuple[str, ...] = ()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                length = int(self.headers["content-length"])
                body = json.loads(self.rfile.read(length).decode("utf-8"))
                response = owner._respond(body)
                encoded = json.dumps(response, separators=(",", ":")).encode("utf-8")
                self.send_response(200)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(encoded)))
                self.send_header(
                    "x-request-id",
                    f"f7c1-http-{len(owner.request_kinds)}",
                )
                self.end_headers()
                self.wfile.write(encoded)

            def log_message(self, format: str, *args: object) -> None:
                del format, args

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        host, port = self.server.server_address
        return f"http://{host}:{port}/v1"

    def __enter__(self) -> Self:
        self.thread.start()
        return self

    def __exit__(self, *args: object) -> None:
        del args
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def _respond(self, body: dict[str, Any]) -> dict[str, object]:
        messages = body["messages"]
        if "response_format" in body:
            self.request_kinds.append("plan")
            prompt = messages[-1]["content"]
            planning_input = json.loads(prompt.split("\n", 1)[1])
            constraints = planning_input["constraints"]
            symbol_ref = next(
                reference
                for reference in constraints["allowed_evidence_refs"]
                if reference.startswith("symbol:demo_app/core.py:")
                and reference.endswith(".feature_status")
            )
            acceptance_ref = next(
                reference
                for reference in constraints["allowed_evidence_refs"]
                if reference.startswith("artifact:acceptance_criteria@")
            )
            symbol_identity = symbol_ref.removeprefix("symbol:").split(":")
            plan = {
                "objective": "Change the validated feature_status behavior through the public path",
                "acceptance_criteria": [
                    {
                        "order": 1,
                        "criterion_id": "public-ready",
                        "description": "feature_status returns the public-ready value",
                        "evidence_refs": [acceptance_ref],
                    }
                ],
                "targets": [
                    {
                        "target_id": "feature-status",
                        "path": symbol_identity[0],
                        "symbol": symbol_identity[-1],
                        "change_kind": "modify",
                        "evidence_refs": [symbol_ref],
                    }
                ],
                "steps": [
                    {
                        "order": 1,
                        "step_id": "implement-feature-status",
                        "description": "Apply the smallest evidence-bound feature_status change",
                        "target_ids": ["feature-status"],
                        "tools": ["apply_patch"],
                    }
                ],
                "planned_tools": ["apply_patch"],
                "risks": [
                    {
                        "risk_id": "behavior-regression",
                        "description": "The public status behavior could regress",
                        "mitigation": "Run every compiled verification gate",
                    }
                ],
                "applicable_gates": constraints["applicable_gates"],
                "rollback_strategy": {
                    "triggers": ["A required verification gate fails"],
                    "actions": ["Revert only the promoted candidate commit"],
                    "verification": ["Confirm the baseline behavior is restored"],
                },
                "completion_conditions": [
                    {
                        "condition_id": "public-ready-complete",
                        "criterion_id": "public-ready",
                        "description": "The acceptance test proves public-ready behavior",
                    }
                ],
                "remaining_gaps": [],
            }
            return _chat_response(
                request_number=len(self.request_kinds),
                content=json.dumps(plan, separators=(",", ":")),
            )

        tools = body["tools"]
        self.tool_names = tuple(tool["function"]["name"] for tool in tools)
        if messages[-1]["role"] == "tool":
            self.request_kinds.append("continuation")
            return _chat_response(
                request_number=len(self.request_kinds),
                content="Public feature implemented through the governed tool loop",
            )

        self.request_kinds.append("tool_call")
        patch = (
            "--- a/demo_app/core.py\n"
            "+++ b/demo_app/core.py\n"
            "@@ -2,4 +2,4 @@\n"
            " \n"
            " \n"
            " def feature_status() -> str:\n"
            "-    return \"baseline-ready\"\n"
            "+    return \"public-ready\"\n"
        )
        arguments = {
            "path": "demo_app/core.py",
            "patch": patch,
            "expected_sha256": self.expected_sha256,
        }
        return _chat_response(
            request_number=len(self.request_kinds),
            tool_calls=[
                {
                    "id": "f7c1-apply-feature",
                    "type": "function",
                    "function": {
                        "name": "apply_patch",
                        "arguments": json.dumps(arguments, separators=(",", ":")),
                    },
                }
            ],
        )


def test_installed_public_cli_delivers_promotes_audits_and_rolls_back(
    tmp_path: Path,
) -> None:
    command_temp = tmp_path / "command-temp"
    command_temp.mkdir()
    local_appdata = tmp_path.parent / "la"
    local_appdata.mkdir()
    command_environment = os.environ.copy()
    for variable in ("TEMP", "TMP", "TMPDIR"):
        command_environment[variable] = str(command_temp)

    repository = tmp_path / "external-repository"
    (repository / "demo_app").mkdir(parents=True)
    (repository / "tests").mkdir()
    (repository / "demo_app" / "__init__.py").write_text("", encoding="utf-8")
    core = repository / "demo_app" / "core.py"
    core.write_text(_BASE_APPLICATION, encoding="utf-8")
    (repository / "tests" / "test_core.py").write_text(_BASE_TEST, encoding="utf-8")
    (repository / "pyproject.toml").write_text(_PROJECT_TOML, encoding="utf-8")
    (repository / ".gitignore").write_text(_GITIGNORE, encoding="utf-8")

    _git(repository, "init", "--quiet")
    _git(repository, "config", "user.name", "F7.C1 Public Product Test")
    _git(repository, "config", "user.email", "f7c1-product@example.invalid")
    _git(repository, "add", "--all", "--", ".")
    _git(repository, "commit", "--quiet", "-m", "baseline external repository")

    distribution = tmp_path / "distribution"
    distribution.mkdir()
    installed_environment = tmp_path / "installed-wheel-environment"
    installed_environment.mkdir()
    _build_and_install_wheel(
        distribution=distribution,
        installed_environment=installed_environment,
        command_environment=command_environment,
    )
    command_environment["LOCALAPPDATA"] = str(local_appdata)

    environment = command_environment.copy()
    environment["PYTHONPATH"] = str(installed_environment)
    environment["PYTHONNOUSERSITE"] = "1"
    environment["PYTHONSAFEPATH"] = "1"
    scripts_dir = Path(sys.executable).parent
    environment["PATH"] = os.pathsep.join((str(scripts_dir), environment.get("PATH", "")))
    cli = [sys.executable, "-m", "ai_engineering_harness.cli.main"]

    origin = _run(
        [
            sys.executable,
            "-c",
            "import ai_engineering_harness as h; print(h.__file__)",
        ],
        cwd=repository,
        environment=environment,
    )
    package_origin = Path(origin.stdout.strip()).resolve(strict=True)
    assert installed_environment in package_origin.parents
    assert ROOT not in package_origin.parents

    init = _run([*cli, "init"], cwd=repository, environment=environment)
    assert "inicializada com sucesso" in init.stdout
    graph = repository / ".harness" / "graphs" / "specs" / "new-feature.yaml"
    assert "entrypoint: implement_feature" in graph.read_text(encoding="utf-8")
    (repository / ".harness" / "policies" / "verification_policy.yaml").write_text(
        _VERIFICATION_POLICY,
        encoding="utf-8",
    )
    artifacts = repository / ".harness" / "knowledge" / "artifacts"
    for artifact_id in (
        "prd",
        "domain_model",
        "non_functional_requirements",
        "acceptance_criteria",
        "architecture",
    ):
        (artifacts / f"{artifact_id}.md").write_text(
            f"# {artifact_id}\n\nThe feature_status behavior must become public-ready.\n",
            encoding="utf-8",
        )
    _git(repository, "add", "--all", "--", ".")
    _git(repository, "commit", "--quiet", "-m", "configure public harness workflow")
    base_sha = _git(repository, "rev-parse", "HEAD").stdout.strip().lower()
    baseline = core.read_bytes()

    indexed = _run([*cli, "index"], cwd=repository, environment=environment)
    assert base_sha in indexed.stdout
    assert _git(repository, "status", "--porcelain").stdout == ""

    with _ControlledModelServer(
        expected_sha256=hashlib.sha256(baseline).hexdigest()
    ) as model_server:
        config = {
            "data_egress": {"allowed_providers": ["local"]},
            "models": {
                "providers": {
                    "local": {
                        "adapter": "local",
                        "model": "f7c1-controlled-local",
                        "base_url": model_server.base_url,
                    }
                },
                "routing": {
                    "primary_provider": "local",
                    "fallback_providers": [],
                },
            },
            "budget": {"max_tool_calls": 4},
        }
        try:
            started = _run(
                [
                    *cli,
                    "run",
                    "new-feature",
                    "--intent",
                    "feature_status",
                    "--requirement-id",
                    "f7c1-public-feature",
                    "--affected-file",
                    "demo_app/core.py",
                    "--acceptance-criterion",
                    "feature_status returns public-ready",
                    "--allow-promotion",
                    "--config-json",
                    json.dumps(config, separators=(",", ":")),
                ],
                cwd=repository,
                environment=environment,
            )
        except AssertionError as exc:
            raise AssertionError(
                f"{exc}\ncontrolled model requests: {model_server.request_kinds}"
            ) from exc

    match = re.search(r"Execution ID:\s+([A-Za-z0-9._-]+)", started.stdout)
    assert match is not None, started.stdout
    execution_id = match.group(1).rstrip(".")
    assert "concluiu a travessia" in started.stdout
    assert model_server.request_kinds == ["plan", "tool_call", "continuation"]
    assert set(model_server.tool_names) == {
        "apply_patch",
        "git_diff",
        "git_status",
        "list_files",
        "read_file",
        "run_command",
        "search_text",
    }
    assert core.read_bytes() == baseline

    reference = json.loads(
        (
            repository
            / ".harness"
            / "state"
            / "worktree-references"
            / f"{execution_id}.json"
        ).read_text(encoding="utf-8")
    )
    worktree = Path(reference["worktree_path"])
    changed = (worktree / "demo_app" / "core.py").read_bytes()
    assert b"public-ready" in changed
    assert (worktree / ".harness" / "knowledge" / "current.json").is_file()

    candidate = _run(
        [*cli, "candidate", execution_id, "--message", "feat: public F7.C1 candidate"],
        cwd=repository,
        environment=environment,
    )
    assert "Candidate" in candidate.stdout
    verified = _run([*cli, "verify", execution_id], cwd=repository, environment=environment)
    assert "Aprovados: 3/3" in verified.stdout
    requested = _run(
        [
            *cli,
            "request-promotion",
            execution_id,
            "--reason",
            "exact candidate and four gates reviewed",
        ],
        cwd=repository,
        environment=environment,
    )
    assert "PENDING" in requested.stdout
    approved = _run(
        [*cli, "approve", execution_id, "--approver", "f7c1-reviewer"],
        cwd=repository,
        environment=environment,
    )
    assert "aprovada" in approved.stdout
    promoted = _run([*cli, "promote", execution_id], cwd=repository, environment=environment)
    assert "COMPLETED" in promoted.stdout
    assert core.read_bytes() == changed

    evidence = _run(
        [*cli, "evidence", execution_id, "--verify"],
        cwd=repository,
        environment=environment,
    )
    assert "PROMOTED" in evidence.stdout
    audit = _run([*cli, "audit", execution_id], cwd=repository, environment=environment)
    assert "AUDIT SUCCESS" in audit.stdout
    rolled_back = _run(
        [*cli, "rollback", execution_id],
        cwd=repository,
        environment=environment,
    )
    assert "COMPENSATED" in rolled_back.stdout
    assert core.read_bytes() == baseline
    assert _git(repository, "status", "--porcelain").stdout == ""

    cleaned = _run(
        [*cli, "cleanup-worktree", execution_id],
        cwd=repository,
        environment=environment,
    )
    assert "REMOVED" in cleaned.stdout
    assert not worktree.exists()
