# AI-Engineering-Harness

> **Motor Agentic Autônomo, Local-First e Instalável**

O **AI-Engineering-Harness** transforma qualquer repositório de software em um ambiente governado por agentes autônomos locais através da fórmula:

$$\text{Harness} = \text{BMAD} \longrightarrow \text{Graph Engineering} \longrightarrow \text{MAF} \longrightarrow \text{Serena + Codebase-Memory} \longrightarrow \text{Quality/Ops}$$

---

## ⚡ Ciclo de Vida Agentic Autônomo

O Harness executa o desenvolvimento de software através de um ciclo rigoroso de 11 estágios com verificação determinística e diário de auditoria append-only:

1. **Context Assembly (`ContextAssembler`):** Validação semântica e estrutural do contexto antes de qualquer ação.
2. **Planejamento Tático (`Planner`):** Geração do plano de execução `plan.json` assinado pela persona **Winston (Architect)**.
3. **Execução Segura (`AgentExecutor` + `ToolRouter`):** Agente **Amelia (Developer)** interage através do guardião de permissões `ToolRouter` (MCP Serena / Terminal).
4. **Verificação Poliglota (`VerificationEngine`):** Gates determinísticos de tipo (`mypy`), estilo (`ruff`) e testes (`pytest`).
5. **Loop de Reparo Automático:** Retentativas governadas por limites de custo e iterações (`retry_cost_policy.yaml`).
6. **Promoção e Evidência (`PromotionManager`):** Registro de `evidence.json`, reindexação AST e sync de conhecimento.
7. **Compensação Append-Only (`RollbackManager`):** Reversão controlada com rastreabilidade 100% preservada na Hash Chain SHA-256.

---

## 🚀 Instalação Rápida em Qualquer Repositório

```bash
# 1. Criar/sincronizar o ambiente local a partir do lockfile
uv sync --all-extras

# 2. Inicializar a estrutura .harness/ no repositório de produto
uv run harness init

# 3. Executar o probe de saúde dos 6 estágios
uv run harness doctor

# 4. Executar um workflow agentic autônomo
uv run harness run new-feature
```

---

## Ambiente de desenvolvimento reproduzível

Pré-requisitos:

- Python 3.11, 3.12, 3.13 ou 3.14;
- `uv` 0.11.32 ou superior;
- Git.

O arquivo `uv.lock` é versionado e deve permanecer sincronizado com `pyproject.toml`. Após clonar o
repositório, execute:

```bash
uv sync --all-extras
uv lock --check
uv run python -m pytest
uv run python -m mypy src
uv run python -m ruff check .
uv run python -m build
```

O `uv` cria `.venv` localmente. Não é necessário ativar o ambiente: `uv run` executa cada comando no
ambiente sincronizado. Alterações de dependências devem atualizar `pyproject.toml` e `uv.lock` na mesma
mudança.

---

## Contrato de versionamento

A versão do pacote é definida em `pyproject.toml`. Em runtime, tanto
`ai_engineering_harness.__version__` quanto `harness --version` leem a metadata da distribuição
instalada; nenhum deles mantém um literal independente.

Versões serializadas evoluem separadamente: `graph_schema_version`, `artifact_schema_version` e
`policy_schema_version` identificam seus respectivos contratos. `definition_version` identifica a
revisão de uma definição padrão e não deve ser comparada com a versão do pacote ou de um schema.

---

## 📚 Documentação e Guias

- **Modelo Operacional & Ciclo Agentic:** [agentic_operating_model.md](file:///c:/Users/walla/OneDrive/Desktop/ai-engineering-harness/docs/agentic_operating_model.md)
- **Matriz de Auditoria do Ciclo:** [agentic_lifecycle_audit.md](file:///c:/Users/walla/OneDrive/Desktop/ai-engineering-harness/docs/agentic_lifecycle_audit.md)
- **Especificação Arquitetural:** [harness_architecture_spec.md](file:///c:/Users/walla/OneDrive/Desktop/ai-engineering-harness/docs/harness_architecture_spec.md)
- **Guia do Usuário CLI:** [user_guide.md](file:///c:/Users/walla/OneDrive/Desktop/ai-engineering-harness/docs/user_guide.md)
