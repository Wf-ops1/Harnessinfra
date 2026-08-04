"""Inspeciona e instala a wheel em um ambiente uv isolado."""

from __future__ import annotations

import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "dist"
PROBE = """
import json
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

import ai_engineering_harness

metadata_version = version("ai-engineering-harness")
package_version = ai_engineering_harness.__version__
origin = Path(ai_engineering_harness.__file__).resolve()
workspace = Path.cwd().resolve()
cli = subprocess.run(
    [sys.executable, "-m", "ai_engineering_harness.cli.main", "--version"],
    check=False,
    capture_output=True,
    text=True,
)

assert metadata_version == package_version
assert cli.returncode == 0, cli.stderr
assert cli.stdout.strip() == f"harness, version {metadata_version}"
assert workspace != origin and workspace not in origin.parents, origin
print(
    json.dumps(
        {
            "metadata_version": metadata_version,
            "package_version": package_version,
            "cli": cli.stdout.strip(),
            "origin": str(origin),
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


def _assert_artifact_is_clean(wheel: Path) -> None:
    with zipfile.ZipFile(wheel) as archive:
        invalid = [
            name
            for name in archive.namelist()
            if "__pycache__" in name or name.endswith((".pyc", ".pyo"))
        ]
    if invalid:
        raise RuntimeError(f"Wheel contém bytecode dependente da máquina: {invalid}")


def main() -> None:
    wheel = _find_wheel()
    _assert_artifact_is_clean(wheel)
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
        raise RuntimeError(result.stderr.strip() or "Smoke isolado da wheel falhou sem stderr.")


if __name__ == "__main__":
    main()
