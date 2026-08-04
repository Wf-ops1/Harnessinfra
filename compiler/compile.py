#!/usr/bin/env python3
"""
Graph Compiler CLI
------------------
Compila especificações declarativas de grafos (YAML) em especificações imutáveis do MAF (JSON).
Árbitro em design-time: valida contratos, políticas de ferramentas e injeta gates de verificação.
"""

import argparse
import json
import sys
from contextlib import suppress
from pathlib import Path

# Garante que o diretório raiz esteja no sys.path para importações
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Configura stdout para UTF-8 no Windows se necessário
if hasattr(sys.stdout, "reconfigure"):
    with suppress(AttributeError, OSError, ValueError):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

import yaml

from compiler.validators.contract_validator import ContractValidationError, ContractValidator
from compiler.validators.gate_injector import GateInjector
from compiler.validators.policy_validator import PolicyValidationError, PolicyValidator


def main() -> None:
    parser = argparse.ArgumentParser(description="Graph Compiler for ai-engineering-harness")
    parser.add_argument("--graph", required=True, help="Caminho relativo para o arquivo spec do grafo (YAML)")
    args = parser.parse_args()

    root_dir = ROOT_DIR
    graph_path = root_dir / args.graph

    if not graph_path.exists():
        print(f"❌ Erro: Arquivo de grafo '{args.graph}' não foi encontrado.", file=sys.stderr)
        sys.exit(1)

    print(f"🏗️  Iniciando compilação do grafo em design-time: {args.graph}")

    try:
        with open(graph_path, "r", encoding="utf-8") as f:
            graph_spec = yaml.safe_load(f)

        # 1. Validação de Contratos
        contract_validator = ContractValidator(root_dir)
        contract_validator.validate(graph_spec)
        print("  ✅ [1/4] Todos os contratos Pydantic referenciados foram validados.")

        # 2. Validação de Políticas
        policies_list = []
        for pol_path in graph_spec.get("policies", []):
            full_pol_path = root_dir / pol_path
            if not full_pol_path.exists():
                full_pol_path = root_dir / "src" / "ai_engineering_harness" / "defaults" / pol_path
            if not full_pol_path.exists():
                full_pol_path = root_dir / ".harness" / pol_path
            if full_pol_path.exists():
                with open(full_pol_path, "r", encoding="utf-8") as pf:
                    policies_list.append(yaml.safe_load(pf))

        policy_validator = PolicyValidator(policies_list)
        policy_validator.validate(graph_spec)
        print("  ✅ [2/4] Todas as políticas de ferramentas e papéis foram validadas.")

        # 3. Injeção de Verification Gates
        verification_policy = {}
        verif_path = root_dir / "policies" / "verification_policy.yaml"
        if not verif_path.exists():
            verif_path = root_dir / "src" / "ai_engineering_harness" / "defaults" / "policies" / "verification_policy.yaml"
        if not verif_path.exists():
            verif_path = root_dir / ".harness" / "policies" / "verification_policy.yaml"
        if verif_path.exists():
            with open(verif_path, "r", encoding="utf-8") as vf:
                verification_policy = yaml.safe_load(vf)

        injector = GateInjector(verification_policy)
        compiled_nodes = injector.inject_gates(graph_spec.get("nodes", []))
        print("  ✅ [3/4] Verification Gates determinísticos injetados com sucesso.")

        # 4. Geração do MAF Workflow Definition (JSON imutável)
        graph_name = graph_spec.get("graph", {}).get("name", "compiled_graph")
        output_dir = root_dir / "graphs" / "compiled"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{graph_name}.maf.json"

        compiled_payload = {
            "maf_schema_version": "1.0.0",
            "graph_metadata": graph_spec.get("graph", {}),
            "compiled_at_utc": "2026-08-03T01:25:00Z",
            "policies_applied": graph_spec.get("policies", []),
            "compiled_nodes": compiled_nodes,
        }

        with open(output_file, "w", encoding="utf-8") as out_f:
            json.dump(compiled_payload, out_f, indent=2, ensure_ascii=False)

        print(f"  ✅ [4/4] MAF Workflow Definition imutável gerado em: {output_file.relative_to(root_dir)}")
        print(f"🎉 Compilação concluída com sucesso! O grafo '{graph_name}' está pronto para execução no MAF Runtime.")

    except (ContractValidationError, PolicyValidationError) as e:
        print(f"❌ Falha de Validação em Design-Time: {e}", file=sys.stderr)
        sys.exit(2)
    except (AttributeError, KeyError, OSError, TypeError, ValueError, yaml.YAMLError) as e:
        print(f"💥 Erro inesperado durante a compilação: {e}", file=sys.stderr)
        sys.exit(3)


if __name__ == "__main__":
    main()
