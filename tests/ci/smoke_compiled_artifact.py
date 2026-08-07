"""Compile and reject incompatible or tampered artifacts from the isolated wheel."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "dist"
PROBE = r'''
import json
import tempfile
from pathlib import Path

import ai_engineering_harness
from ai_engineering_harness.compiler import GraphCompiler
from ai_engineering_harness.runtime.maf_adapter import (
    ArtifactCompatibilityError,
    ArtifactIntegrityError,
    MAFAdapter,
)

GRAPH = """
graph:
  name: wheel-smoke
  graph_schema_version: "1.0"
  definition_version: "1.0.0"
  entrypoint: verify
  status: stable
nodes:
  - id: verify
    type: deterministic
    executor: deterministic_gate
    gate_name: verified
    on_success: completed
    on_failure: failed
terminal_states:
  - id: completed
    outcome: success
  - id: failed
    outcome: failure
policies: []
contracts: []
"""

origin = Path(ai_engineering_harness.__file__).resolve()
checkout = Path.cwd().resolve()
assert checkout != origin and checkout not in origin.parents, origin

with tempfile.TemporaryDirectory(prefix="harness-f1.5-wheel-") as temporary:
    project = Path(temporary).resolve()
    source = project / "graph.yaml"
    source.write_text(GRAPH, encoding="utf-8")
    compiler = GraphCompiler(project)
    output = compiler.compile_graph(source)
    artifact = MAFAdapter.load_and_validate(output)
    assert artifact.artifact_schema_version == "2.0"
    assert artifact.graph.graph.name == "wheel-smoke"
    assert artifact.source_manifest

    tampered = json.loads(output.read_text(encoding="utf-8"))
    tampered["graph_digest"] = "sha256:" + "0" * 64
    output.write_text(json.dumps(tampered, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        MAFAdapter.load_and_validate(output)
    except ArtifactIntegrityError:
        pass
    else:
        raise AssertionError("tampered artifact was accepted")

    output = compiler.compile_graph(source)
    incompatible = json.loads(output.read_text(encoding="utf-8"))
    incompatible["package_version"] = "999.0.0"
    output.write_text(json.dumps(incompatible, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        MAFAdapter.load_and_validate(output)
    except ArtifactCompatibilityError:
        pass
    else:
        raise AssertionError("incompatible artifact was accepted")

    print(
        json.dumps(
            {
                "artifact_schema_version": artifact.artifact_schema_version,
                "manifest_entries": len(artifact.source_manifest),
                "origin": str(origin),
                "tamper_rejected": True,
                "version_rejected": True,
            },
            sort_keys=True,
        )
    )
'''


def _find_wheel() -> Path:
    wheels = sorted(DIST.glob("*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"Esperada exatamente uma wheel em {DIST}; encontradas: {wheels}")
    return wheels[0]


def main() -> None:
    wheel = _find_wheel()
    result = subprocess.run(
        [
            "uv",
            "run",
            "--isolated",
            "--no-project",
            "--with",
            str(wheel.resolve()),
            "python",
            "-c",
            PROBE,
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.stdout:
        print(result.stdout.strip())
    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip() or "Smoke isolado do artefato compilado falhou sem stderr."
        )


if __name__ == "__main__":
    main()
