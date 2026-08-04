"""Smoke test for importing every public module shipped by the package."""

from __future__ import annotations

import importlib
import sys
import traceback
import unittest
from pathlib import Path

PACKAGE_NAME = "ai_engineering_harness"
SRC_ROOT = Path(__file__).resolve().parents[2] / "src"
PACKAGE_ROOT = SRC_ROOT / PACKAGE_NAME


def _public_module_names() -> list[str]:
    """Return every module whose path does not contain a private component."""
    modules: set[str] = set()

    for module_path in PACKAGE_ROOT.rglob("*.py"):
        relative_path = module_path.relative_to(PACKAGE_ROOT)
        relative_parts = relative_path.parts

        if any(part.startswith("_") and part != "__init__.py" for part in relative_parts):
            continue

        if module_path.name == "__init__.py":
            module_parts = relative_parts[:-1]
        else:
            module_parts = (*relative_parts[:-1], module_path.stem)

        modules.add(".".join((PACKAGE_NAME, *module_parts)))

    return sorted(modules)


class PublicModuleImportTests(unittest.TestCase):
    def test_all_public_modules_import(self) -> None:
        source_path = str(SRC_ROOT)
        if source_path not in sys.path:
            sys.path.insert(0, source_path)

        failures: list[str] = []
        module_names = _public_module_names()

        self.assertTrue(module_names, "No public package modules were discovered")

        for module_name in module_names:
            try:
                importlib.import_module(module_name)
            except Exception:  # noqa: BLE001 - aggregate every broken public import
                failures.append(f"{module_name}\n{traceback.format_exc()}")

        self.assertFalse(
            failures,
            "Public modules failed to import:\n\n" + "\n".join(failures),
        )


if __name__ == "__main__":
    unittest.main()
