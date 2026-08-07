#!/usr/bin/env python3
"""Compatibility CLI delegating to the package graph compiler."""

import argparse
import sys
from contextlib import suppress
from pathlib import Path

from ai_engineering_harness.compiler import GraphCompiler, GraphCompilerError

if hasattr(sys.stdout, "reconfigure"):
    with suppress(AttributeError, OSError, ValueError):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile a graph with ai-engineering-harness")
    parser.add_argument("--graph", required=True, help="Graph YAML path relative to the project root")
    args = parser.parse_args()

    try:
        output_file = GraphCompiler(Path.cwd()).compile_graph(Path(args.graph))
    except GraphCompilerError as exc:
        parser.exit(2, f"Graph compilation failed: {exc}\n")
    print(f"Compiled graph: {output_file.relative_to(Path.cwd().resolve())}")


if __name__ == "__main__":
    main()
