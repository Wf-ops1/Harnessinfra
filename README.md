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
# 1. Instalar o harness em modo editável ou via pip
pip install -e .

# 2. Inicializar a estrutura .harness/ no repositório de produto
harness init

# 3. Executar o probe de saúde dos 6 estágios
harness doctor

# 4. Executar um workflow agentic autônomo
harness run new-feature
```

---

## 📚 Documentação e Guias

- **Modelo Operacional & Ciclo Agentic:** [agentic_operating_model.md](file:///c:/Users/walla/OneDrive/Desktop/ai-engineering-harness/docs/agentic_operating_model.md)
- **Matriz de Auditoria do Ciclo:** [agentic_lifecycle_audit.md](file:///c:/Users/walla/OneDrive/Desktop/ai-engineering-harness/docs/agentic_lifecycle_audit.md)
- **Especificação Arquitetural:** [harness_architecture_spec.md](file:///c:/Users/walla/OneDrive/Desktop/ai-engineering-harness/docs/harness_architecture_spec.md)
- **Guia do Usuário CLI:** [user_guide.md](file:///c:/Users/walla/OneDrive/Desktop/ai-engineering-harness/docs/user_guide.md)
