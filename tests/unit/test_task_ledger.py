"""Structural regressions for the short task panel and archived dossiers."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TASK_PANEL = ROOT / "TASK.md"
TASKS_ROOT = ROOT / "docs" / "tasks"
ACTIVE_ROOT = TASKS_ROOT / "active"
COMPLETED_ROOT = TASKS_ROOT / "completed"
MANIFEST_PATH = TASKS_ROOT / "migration-manifest.json"
EXPECTED_TASK_IDS = {
    "F0.0",
    "F0.1",
    "F0.2",
    "F0.3",
    "F0.4",
    "F0.5",
    "F0.6",
    "F1.1",
    "F1.2",
    "F1.3",
    "F1.4",
    "F1.5",
    "F2.1",
    "F2.2",
    "F2.3",
    "F2.4",
    "F2.5",
    "F2.6",
    "DOC-F2-STATUS",
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="strict")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_task_panel_is_a_bounded_current_control_plane() -> None:
    panel = _read(TASK_PANEL)
    lines = panel.splitlines()
    active_dossiers = sorted(
        path for path in ACTIVE_ROOT.glob("*.md") if path.name != "README.md"
    )

    assert len(lines) <= 300
    assert panel.count("## 7. Próxima ação exata") == 1
    assert panel.count("## 5. Tarefa ativa") == 1
    assert "defensibility:" not in panel
    assert re.search(r"(?m)^### F[0-9]+\.[0-9]+\b", panel) is None

    if active_dossiers:
        assert len(active_dossiers) == 1
        assert active_dossiers[0].relative_to(ROOT).as_posix() in panel
    else:
        assert "nenhuma tarefa ativa" in panel.casefold()


def test_there_is_at_most_one_active_dossier() -> None:
    active_dossiers = sorted(
        path for path in ACTIVE_ROOT.glob("*.md") if path.name != "README.md"
    )

    assert len(active_dossiers) <= 1


def test_completed_dossiers_match_the_integrity_manifest() -> None:
    manifest = json.loads(_read(MANIFEST_PATH))
    entries = manifest["entries"]
    markers = manifest["payload_markers"]

    assert manifest["schema_version"] == "1.0"
    assert manifest["source"] == {
        "commit": "d48151b752aa373756c46bfee58932fa5abf4bf5",
        "normalization": "section payload rstrip followed by one LF",
        "path": "TASK.md",
        "sha256": "f0f1a18751c0e730f7e6c4b6335192e0a655e06bba88e6996f9419270112d309",
    }
    assert len(entries) == len(EXPECTED_TASK_IDS)
    assert {entry["task_id"] for entry in entries} == EXPECTED_TASK_IDS
    assert len({entry["path"] for entry in entries}) == len(entries)

    completed_paths = {
        path.relative_to(ROOT).as_posix() for path in COMPLETED_ROOT.glob("*.md")
    }
    assert {entry["path"] for entry in entries} <= completed_paths

    for entry in entries:
        dossier = _read(ROOT / entry["path"])
        start_marker = markers["start"] + "\n"
        end_marker = markers["end"]
        assert dossier.count(markers["start"]) == 1
        assert dossier.count(end_marker) == 1
        payload = dossier.split(start_marker, 1)[1].split(end_marker, 1)[0]
        assert payload.splitlines()[0] == entry["source_heading"]
        assert _sha256(payload) == entry["payload_sha256"]


def test_agent_rules_point_to_the_short_panel_and_active_dossier() -> None:
    rules = _read(ROOT / ".agents" / "AGENTS.md")

    assert "TASK.md` — painel curto" in rules
    assert "dossiê ativo apontado por `TASK.md`" in rules
    assert "docs/tasks/README.md" in rules
    assert "no máximo 300 linhas" in rules
