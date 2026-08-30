# Auditoria do Ciclo de Vida Agentic — Desejado vs. Implementado

> **Status da auditoria:** protótipo em desenvolvimento; Fases 0–6 e F7.1–F7.3 promovidas e
> terminalmente reconciliadas. A composição operacional padrão permanece bloqueio para a release.

A matriz classifica efeitos observáveis no código após a F7.3. “Primitiva real/injetável” significa
que o efeito e sua falha segura possuem testes, mas a CLI padrão ainda não monta sozinha todos os
backends necessários. “Implementado” fica reservado ao caminho que o produto realmente compõe.

| Etapa | Componente atual | Evidência existente | Estado real | Lacuna para o produto |
|---|---|---|---|---|
| Disparo | CLI `run` | Resolve configuração, compila/carrega o artefato e inicia o lifecycle; configuração inválida e registry vazio falham antes de efeitos | Fail-closed, composição incompleta | A corretiva F7.C1 deverá construir provider, tools, worktree, gates e autoridades sem conceder confiança implícita |
| Contexto | `ContextAssembler` + `ExecutionLifecycleService` | Policy compilada, seis dimensões `Decimal`, identidade/digest, partição exata de evidência, `context.json`, eventos e resume possuem testes | F4.3 `PROMOTED` | Snapshot e artefatos continuam pré-requisitos explícitos; indexação automática não é presumida |
| Plano | `Planner` + `ExecutionLifecycleService` | Contrato tipado, structured output, evidência/policies por digest, payload/projeção/eventos antes do nó e resume idempotente | F4.4 `PROMOTED` | Provider efetivo ainda depende da composição F7.C1 |
| Agente/modelo | `AgentExecutor`, `ModelRouter` e adapters | OpenAI Responses e endpoint local fazem HTTP real quando configurados; budget reserva antes do transporte e confirma usage real | Primitiva real/injetável; F5.4 `PROMOTED` | CLI padrão não seleciona e injeta o backend; Anthropic falha explicitamente como indisponível |
| Ferramentas | `PolicyEngine`, `ToolRouter` e factory operacional | default-deny/deny-wins em oito eixos, trust comum, budget, redaction e journal antes do efeito | Primitiva real/injetável; F5.2–F5.5 `PROMOTED` | Lifecycle padrão não constrói o registry nem injeta adapters; aprovação humana de tool permanece distinta da aprovação de promoção |
| Verificação | `VerificationEngine` + lifecycle | Taxonomia única, resolução no worktree, persistência commit-bound e repair targeted → full | F4.5–F4.8 `PROMOTED` | A composição padrão ainda precisa fornecer o worktree e os executores efetivos |
| Reparo | `ExecutionLifecycleService` + `GraphExecutor` | Falha vira `RetryContext` redigido no `on_failure` compilado; schedule, deadline, budgets e crash-resume são duráveis | F4.8 `PROMOTED` | Sem F7.C1, `harness run` não executa reparo autônomo com os backends de produção |
| Aprovação | Lifecycle/FSM | Request liga execution, artefato, plano, diff, SHA, gates, validade e decisão; mismatch/expiry bloqueiam antes do Git | F5.6 `PROMOTED` | A composição não pode fabricar decisão nem converter policy booleana em aprovação humana |
| Promoção | `PromotionManager` + lifecycle | Candidate real, full suite no mesmo SHA, write-ahead/outcome, cherry-pick único e recovery possuem E2E | F3.7 `PROMOTED`; enforcement F5.3/F5.6 `PROMOTED` | Manager e autoridades continuam opt-in até F7.C1 |
| Memória | `PythonAstIndexer` + `CodebaseMemoryAdapter` + `SnapshotManager` | Rebuild de blobs Python do commit e snapshot canônico com SHA/schema/status/digest validados | Backend local implementado | `harness index` é explícito; backend MCP ainda não substitui o backend local nem é composto automaticamente |
| Knowledge sync | `KnowledgeTransaction` | Write-ahead, staging/digest, lock, fencing, pointer swap e recovery fail-closed possuem testes | F6.7 `PROMOTED`; primitiva real | O lifecycle padrão ainda não injeta essa transação |
| Evidência | Journal, `EvidenceManifestManager` e CLIs de inspeção | Schema único, hash/digest, export, manifesto terminal, verificação e nove checkpoints de recovery | F6.1–F6.6 `PROMOTED` | Sem chave ou âncora externa, a proteção continua tamper-evident local |
| Rollback | `RollbackManager` + lifecycle | `git revert --no-edit`, validação de SHA/parent/limpeza, conflito bloqueado e aprovação de hook ligada à tentativa | F5.7 `PROMOTED`; efeito real/injetável | Gates pós-reversão não são recompostos automaticamente pelo caminho padrão |
| Doctor | `HealthChecker` e probes tipados | Sete componentes percorrem seis estágios reais; texto/JSON compartilham resultado, `--workflow` resolve gates e unhealthy retorna não zero | F6.4 `PROMOTED`; read-only real | Provider e MCP live continuam condicionados a configuração, credenciais e serviços externos |
| Produto/CI | E2E externo, matriz canônica e quality gates | F7.1 atravessa wheel→worktree→efeitos→promoção→evidence→rollback; F7.2 cobre 12 camadas; F7.3 exige quality/tests/package/security/cobertura em Windows e Linux | F7.1–F7.3 `PROMOTED` | O E2E monta a fronteira explicitamente com provider determinístico de teste; não prova wiring padrão autônomo |

## Interpretação correta dos testes

Os testes provam as primitivas e suas fronteiras de falha: contexto e plano content-addressed,
providers HTTP controlados, tool loop durável, worktree Git, terminal por `argv`, edição confinada,
Serena MCP contra fixture, verificação/reparo, aprovação ligada ao conteúdo, promoção, knowledge,
evidence, cancelamento e rollback. A F7.2 mantém uma matriz executável desses requisitos, e a F7.3
torna compileall, Ruff, mypy strict, cobertura decisória, secrets, dependências, testes e wheel gates
obrigatórios.

A F7.1 é uma prova vertical instalada em repositório externo descartável, porém seu teste injeta
explicitamente provider, tool router, worktree manager e executores. Portanto ela prova que as
primitivas podem compor o produto, não que a CLI pública já faça essa composição. Essa diferença é o
escopo obrigatório da F7.C1 antes da F7.5.

## Gate para mudar uma linha para “implementada”

Uma etapa só pode ser chamada de implementada no produto quando:

1. o efeito real correspondente existir;
2. indisponibilidade gerar erro tipado e estado bloqueado;
3. side effects estiverem confinados e auditados;
4. houver teste de sucesso e de falha segura;
5. o caminho público compuser a capacidade sem factory específica da fixture;
6. o E2E externo comprovar o comportamento sem adapter simulado registrado em produção.
