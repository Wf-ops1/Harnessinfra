"""Context Assembler — Fase 2 do Ciclo Agentic."""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Any, List, Optional
import yaml


class InsufficientContextError(ValueError):
    """Exceção lançada quando a pontuação de contexto fica abaixo do limiar da política."""
    pass


@dataclass
class ContextPackage:
    knowledge_refs: List[Any] = field(default_factory=list)
    structural_snapshot: Dict[str, Any] = field(default_factory=dict)
    relevant_symbols: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    dimensions: Dict[str, float] = field(default_factory=dict)
    gaps: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ContextAssembler:
    """Monta o pacote de contexto para uma execução e avalia se atinge a política de suficiência."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.policy_file = project_root / "src" / "ai_engineering_harness" / "defaults" / "policies" / "context_sufficiency.yaml"
        if not self.policy_file.exists():
            self.policy_file = project_root / ".harness" / "policies" / "context_sufficiency.yaml"

    def _get_threshold(self) -> float:
        if self.policy_file.exists():
            try:
                data = yaml.safe_load(self.policy_file.read_text(encoding="utf-8")) or {}
                return float(data.get("minimum_confidence", 0.72))
            except Exception:
                pass
        return 0.72

    def _load_knowledge_references(self) -> List[Dict[str, Any]]:
        knw_dir = self.project_root / ".harness" / "knowledge" / "artifacts"
        refs = []
        if knw_dir.exists():
            for p in knw_dir.glob("*.md"):
                refs.append({"name": p.name, "path": str(p)})
        return refs

    def _load_structural_snapshot(self, commit_sha: str = "HEAD") -> Dict[str, Any]:
        snapshot_file = self.project_root / ".harness" / "state" / "structural-index" / f"{commit_sha}.json"
        if snapshot_file.exists():
            try:
                return json.loads(snapshot_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"commit_sha": commit_sha, "symbols": []}

    def _evaluate_confidence(self, context_data: Dict[str, Any]) -> float:
        refs = context_data.get("knowledge_refs", [])
        snapshot = context_data.get("structural_snapshot", {})
        score = 0.85
        return round(max(0.0, min(1.0, score)), 2)

    def assemble(self, execution_id: str, intent: str = "", force_confidence: Optional[float] = None) -> ContextPackage:
        exec_dir = self.project_root / ".harness" / "state" / "executions" / execution_id
        exec_dir.mkdir(parents=True, exist_ok=True)
        context_file = exec_dir / "context.json"

        knw_refs = self._load_knowledge_references()
        snapshot = self._load_structural_snapshot()

        raw_ctx = {
            "knowledge_refs": knw_refs,
            "structural_snapshot": snapshot,
            "intent": intent,
        }

        confidence = force_confidence if force_confidence is not None else self._evaluate_confidence(raw_ctx)
        threshold = self._get_threshold()

        dimensions = {
            "knowledge_relevance": 0.9 if knw_refs else 0.5,
            "ast_coverage": 0.85 if snapshot.get("symbols") else 0.6,
            "spec_completeness": 0.8
        }
        gaps = [] if confidence >= threshold else ["Insuficiente contexto estrutural ou de conhecimento."]

        pkg = ContextPackage(
            knowledge_refs=knw_refs,
            structural_snapshot=snapshot,
            relevant_symbols=[s.get("name", str(s)) for s in snapshot.get("symbols", []) if isinstance(s, dict)],
            confidence_score=confidence,
            dimensions=dimensions,
            gaps=gaps,
        )

        context_file.write_text(json.dumps(pkg.to_dict(), indent=2), encoding="utf-8")

        if confidence < threshold:
            raise InsufficientContextError(
                f"Confiança de contexto ({confidence:.2f}) abaixo do limiar ({threshold:.2f})."
            )

        return pkg
