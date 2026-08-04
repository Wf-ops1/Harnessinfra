# Auditoria do Ciclo de Vida Agentic — Desejado vs. Implementado

> **Status da auditoria: Protótipo / Em desenvolvimento**

A matriz abaixo classifica efeitos observáveis no código atual. “Experimental” significa que existe
estrutura executável ou teste, mas a etapa ainda depende de simulação, sequência fixa ou garantia
incompleta. “Planejada” aponta para a fase responsável no plano operacional.

| Etapa | Componente atual | Evidência existente | Estado real | Lacuna para o produto |
|---|---|---|---|---|
| Disparo | CLI `run` | Cria `execution_id` e chama o runtime | Experimental | Falta validar repositório, configuração e precondições fail-closed |
| Contexto | `ContextAssembler` | Persiste `context.json` | Experimental | Score é heurístico; contexto estrutural/semântico real fica para F4 |
| Plano | `Planner` | Persiste `plan.json` | Experimental | Não nasce de provider real nem governa efeitos com pre/postcondições completas |
| Agente/modelo | `AgentExecutor` e adapters | Router e tipos existem | Simulado | Adapters fabricam respostas e não executam modelo real; F3 |
| Ferramentas | `ToolRouter` e adapters | Allowlist e dispatch possuem testes | Simulado/inseguro | Serena não é MCP e terminal usa `shell=True`; F3/F5 |
| Verificação | `VerificationEngine` | Executa subprocessos para gates selecionados | Experimental | Lista vazia pode passar; política fail-closed e gates completos ficam para F4 |
| Reparo | Loop no `RuntimeEngine` | Respeita limite de tentativas | Experimental | Repete a mesma chamada; não produz e verifica patch corretivo real |
| Aprovação | `ApprovalManager` | Solicitação/decisão são persistidas | Experimental | Aprovar não retoma/promove por protocolo persistido; F2/F3/F5 |
| Promoção | `PromotionManager` | Registra evento e retorna string | Simulado | Runtime força dry-run e recebe SHA sintético; caminho live possui fallbacks sintéticos |
| Memória | `CodebaseMemoryAdapter` | Snapshot local por commit | Simulado | Retorna `mock_ast`; backend estrutural real fica para F3/F4 |
| Knowledge sync | `KnowledgeSynchronizer` | Transação local em etapas | Experimental | Falta integrar backend real, idempotência/recovery e política no caminho crítico |
| Evidência | `RuntimeEngine` e audit trail | `evidence.json` e hash chain locais | Experimental | Evidência pode registrar SHA/efeitos simulados e não prova alteração entregue |
| Rollback | `RollbackManager` | Eventos de compensação e chamada de Git existem | Experimental/inseguro | Worktree não é real; revert recebe string via shell; recovery e gates faltam |
| Doctor | `HealthProbe` | Formato de seis estágios e relatório | Simulado | Todos os estágios retornam OK sem probe; F6 |

## Interpretação correta dos testes

Os testes atuais provam contratos internos e caminhos do protótipo. Eles não provam conectividade com
OpenAI, Anthropic, Ollama, Serena ou Codebase-Memory; não provam isolamento por worktree; e não provam
promoção/reversão sobre um repositório externo. O E2E atual usa diretório temporário, adapters
simulados, gates limitados e promoção dry-run.

## Gate para mudar uma linha para “implementada”

Uma etapa só muda para implementada quando:

1. o efeito real correspondente existir;
2. indisponibilidade gerar erro tipado e estado bloqueado;
3. side effects estiverem confinados e auditados;
4. houver teste de sucesso e de falha segura;
5. o E2E externo comprovar o comportamento sem mocks.
