"""Auto-detecção de stack tecnológica do projeto-alvo."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class DetectedStack(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    language: str
    package_manager: str | None
    test_runner: str | None
    linter: str | None
    build_tool: str | None
    detected_files: list[str]

class StackDetector:
    """Analisa o diretório raiz do projeto para identificar a stack."""

    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or Path.cwd()

    def detect(self) -> DetectedStack:
        files = [f.name for f in self.project_root.iterdir() if f.is_file()]

        # Python
        if "pyproject.toml" in files or "setup.py" in files or "requirements.txt" in files:
            return DetectedStack(
                language="python",
                package_manager="pip/uv/poetry" if "pyproject.toml" in files else "pip",
                test_runner="pytest",
                linter="ruff/mypy",
                build_tool="build/flit/setuptools",
                detected_files=[f for f in ["pyproject.toml", "setup.py", "requirements.txt"] if f in files]
            )

        # Node.js / TypeScript
        if "package.json" in files:
            return DetectedStack(
                language="typescript/javascript",
                package_manager="npm/pnpm/yarn",
                test_runner="vitest/jest",
                linter="eslint",
                build_tool="tsc/vite/next",
                detected_files=["package.json"]
            )

        # Go
        if "go.mod" in files:
            return DetectedStack(
                language="go",
                package_manager="go modules",
                test_runner="go test",
                linter="golangci-lint",
                build_tool="go build",
                detected_files=["go.mod"]
            )

        # Rust
        if "Cargo.toml" in files:
            return DetectedStack(
                language="rust",
                package_manager="cargo",
                test_runner="cargo test",
                linter="cargo clippy",
                build_tool="cargo build",
                detected_files=["Cargo.toml"]
            )

        # Java
        if "pom.xml" in files or "build.gradle" in files or "build.gradle.kts" in files:
            is_maven = "pom.xml" in files
            return DetectedStack(
                language="java",
                package_manager="maven" if is_maven else "gradle",
                test_runner="maven/gradle test",
                linter="checkstyle/spotbugs",
                build_tool="mvn/gradle",
                detected_files=[f for f in ["pom.xml", "build.gradle", "build.gradle.kts"] if f in files]
            )

        # Fallback genérico
        return DetectedStack(
            language="unknown",
            package_manager=None,
            test_runner=None,
            linter=None,
            build_tool=None,
            detected_files=[]
        )
