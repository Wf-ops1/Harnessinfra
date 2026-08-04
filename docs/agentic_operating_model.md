# Modelo Operacional Agentic — Narrative & Architecture

O **AI-Engineering-Harness** é a infraestrutura de engenharia local-first projetada para sustentar o ciclo autônomo de desenvolvimento de software governado por IA.

---

## 🚀 Fluxo de Execução do Ciclo Agentic

```mermaid
sequenceDiagram
    autonumber
    actor User as Desenvolvedor / CLI
    participant Engine as RuntimeEngine
    participant FSM as WorkflowStateMachine
    participant Ctx as ContextAssembler
    participant Plan as Planner (Winston)
    participant Agent as AgentExecutor (Amelia)
    participant Router as ToolRouter
    participant Verifier as VerificationEngine
    participant Promo as PromotionManager
    participant Audit as AuditTrailManager

    User->>Engine: harness run <workflow>
    Engine->>FSM: INITIATED ➔ CONTEXT_ASSEMBLING
    Engine->>Ctx: assemble(execution_id, intent)
    Ctx-->>Engine: ContextPackage (confidence >= 0.72)
    Engine->>FSM: GENERATING_PLAN
    Engine->>Plan: create_plan(context)
    Plan-->>Engine: plan.json (PlanDocument)
    Engine->>FSM: EXECUTING
    Engine->>Agent: execute_node(intent)
    Agent->>Router: execute_tool(serena_edit / terminal_run)
    Router-->>Agent: Resultado de Execução
    Engine->>FSM: VERIFYING
    Engine->>Verifier: verify(active_gates)
    alt Sucesso na Verificação
        Engine->>FSM: PROMOTING
        Engine->>Promo: promote(execution_id)
        Promo-->>Engine: Commit SHA / Evento
        Engine->>FSM: REINDEXING ➔ KNOWLEDGE_SYNC ➔ GENERATING_EVIDENCE
        Engine->>FSM: COMPLETED
    else Falha e Exaustão de Retentativas
        Engine->>FSM: FAILED_RETRY_EXHAUSTED
    end
    Engine->>Audit: log_event(WORKFLOW_COMPLETED)
```

---

## 🛠️ Princípios Fundamentais

1. **Local-First & Instalável:** O pacote `ai-engineering-harness` é totalmente instalável via `pip install -e .` e inicializável em qualquer repositório de produto via `harness init`.
2. **Separação Rígida Agente/Ferramenta:**
   - **Agente (Persona):** Raciocínio, tomada de decisão e invocação de habilidades (ex: Winston, Amelia).
   - **ToolRouter:** Guardião de segurança e permissões para execução de chamadas MCP/terminal.
3. **Audit Trail Tamper-Evident:** Registro append-only encadeado por SHA-256 no diário de eventos.
