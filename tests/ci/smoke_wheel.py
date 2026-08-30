"""Inspeciona e instala a wheel em um ambiente uv isolado."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "dist"
PROBE = """
import json
import subprocess
import sys
from importlib.resources import files
from importlib.metadata import version
from pathlib import Path

import ai_engineering_harness

metadata_version = version("ai-engineering-harness")
package_version = ai_engineering_harness.__version__
origin = Path(ai_engineering_harness.__file__).resolve()
workspace = Path.cwd().resolve()
checkout = Path(sys.argv[1]).resolve()
defaults = files("ai_engineering_harness.defaults")
cli = subprocess.run(
    [sys.executable, "-m", "ai_engineering_harness.cli.main", "--version"],
    check=False,
    capture_output=True,
    text=True,
)

sentinel = workspace / ".harness" / "policies" / "verification_policy.yaml"
sentinel.parent.mkdir(parents=True)
sentinel.write_text("preserve-user-content\\n", encoding="utf-8")
initialized = subprocess.run(
    [sys.executable, "-m", "ai_engineering_harness.cli.main", "init"],
    check=False,
    capture_output=True,
    text=True,
)

assert metadata_version == package_version
assert cli.returncode == 0, cli.stderr
assert cli.stdout.strip() == f"harness, version {metadata_version}"
assert workspace != origin and workspace not in origin.parents, origin
assert checkout != origin and checkout not in origin.parents, origin
assert checkout not in workspace.parents and workspace != checkout, workspace
assert not (workspace / "src" / "ai_engineering_harness").exists()
assert defaults.joinpath("policies").joinpath("verification_policy.yaml").is_file()
assert defaults.joinpath("graphs").joinpath("new-feature.yaml").is_file()
assert initialized.returncode == 0, initialized.stderr
assert sentinel.read_text(encoding="utf-8") == "preserve-user-content\\n"
assert (workspace / ".harness" / "graphs" / "specs" / "new-feature.yaml").is_file()
assert (workspace / ".harness" / "tools" / "tool_registry.yaml").is_file()
print(
    json.dumps(
        {
            "metadata_version": metadata_version,
            "package_version": package_version,
            "cli": cli.stdout.strip(),
            "init": initialized.stdout.strip(),
            "origin": str(origin),
            "workspace": str(workspace),
        },
        sort_keys=True,
    )
)
"""


def _find_wheel() -> Path:
    wheels = sorted(DIST.glob("*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"Esperada exatamente uma wheel em {DIST}; encontradas: {wheels}")
    return wheels[0]


def _uv_executable() -> str:
    configured = os.environ.get("HARNESS_TEST_UV")
    if configured:
        candidate = Path(configured).expanduser()
        if not candidate.is_file():
            raise RuntimeError(f"HARNESS_TEST_UV não aponta para arquivo: {candidate}")
        return str(candidate.resolve())
    discovered = shutil.which("uv")
    if discovered is None:
        raise RuntimeError("uv não encontrado em PATH e HARNESS_TEST_UV não foi definido.")
    return discovered


def _assert_artifact_is_clean(wheel: Path) -> None:
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        invalid = [
            name
            for name in names
            if any(part in {"__pycache__", ".pytest_cache"} for part in Path(name).parts)
            or ".egg-info" in name
            or name.endswith((".pyc", ".pyo"))
        ]
        required = {
            "ai_engineering_harness/defaults/agents/_base/agent_base.yaml",
            "ai_engineering_harness/defaults/graphs/new-feature.yaml",
            "ai_engineering_harness/defaults/policies/verification_policy.yaml",
            "ai_engineering_harness/defaults/tools/tool_registry.yaml",
        }
        license_files = [
            name
            for name in names
            if ".dist-info/" in name and name.endswith(("/LICENSE", "/LICENSE.txt"))
        ]
    if invalid:
        raise RuntimeError(f"Wheel contém bytecode dependente da máquina: {invalid}")
    missing = sorted(required.difference(names))
    if missing:
        raise RuntimeError(f"Wheel não contém recursos obrigatórios: {missing}")
    if not license_files:
        raise RuntimeError("Wheel não contém o texto Apache-2.0 em dist-info.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", nargs="?", type=Path, help="Wheel explícita; padrão: dist/*.whl")
    arguments = parser.parse_args()
    wheel = (arguments.wheel or _find_wheel()).resolve(strict=True)
    _assert_artifact_is_clean(wheel)
    with tempfile.TemporaryDirectory(prefix="harness-wheel-smoke-") as temporary:
        external_root = Path(temporary).resolve()
        result = subprocess.run(
            [
                _uv_executable(),
                "run",
                "--isolated",
                "--no-project",
                "--with",
                str(wheel),
                "python",
                "-c",
                PROBE,
                str(ROOT.resolve()),
            ],
            cwd=external_root,
            check=False,
            capture_output=True,
            text=True,
        )
    if result.stdout:
        print(result.stdout.strip())
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Smoke isolado da wheel falhou sem stderr.")


if __name__ == "__main__":
    main()
