# Auditoria Técnica da Estrutura, Fluxos e Pendências

> **Status:** diagnóstico corrente do MVP operacional / RC `0.2.0rc1`; não é certificação de produção.

## 1. Método

A auditoria considera uma capacidade existente somente quando o código produz o efeito declarado e
há teste correspondente. Nomes de classes, YAMLs, diagramas e estados da FSM são evidência de design,
mas não substituem conectividade, isolamento, side effects reais ou falha segura.

## 2. Consistência da estrutura

| Item documentado anteriormente | Estado observado | Correção |
|---|---|---|
| `task.md` | O arquivo rastreado é `TASK.md` | Referências normalizadas |
| `contracts/` na raiz | Ausente | Contratos reais ficam em `src/ai_engineering_harness/contracts/` |
| `policies/` na raiz | Ausente | Defaults ficam em `src/ai_engineering_harness/defaults/policies/` |
| `graphs/specs/` na raiz | Ausente | Defaults ficam no pacote; specs locais ficam sob `.harness/` após init |
| `observability/log_integrity.py` | Ausente | Integridade está em `observability/audit.py` |
| Contagem fixa de testes | Ficava obsoleta após cada fase | Relatórios agora registram o checkpoint a que a contagem pertence |

## 3. FSM observada

Os estados e transições estão implementados em
[state_machine.py](../src/ai_engineering_harness/runtime/state_machine.py). O caminho principal atual
é:

```text
INITIATED
  -> CONTEXT_ASSEMBLING
  -> GENERATING_PLAN
  -> EXECUTING
  -> VERIFYING
  -> (EXECUTING/VERIFYING em retry)
  -> AWAITING_APPROVAL ou PROMOTING
  -> REINDEXING
  -> KNOWLEDGE_SYNC
  -> GENERATING_EVIDENCE
  -> COMPLETED
```

Para artefatos com a policy F4.3, o prefixo real agora é
`INITIATED → CONTEXT_ASSEMBLING → PLANNING → EXECUTING`; insuficiência desvia para
`BLOCKED_INSUFFICIENT_CONTEXT`, pré-requisito inválido para `BLOCKED_PREREQUISITE` e uma quarta
solicitação após três decisões persistidas leva a `FAILED_RETRY_EXHAUSTED`. O grafo maior acima
descreve a FSM legada, não o fluxo padrão atual da CLI nem efeitos garantidos. O lifecycle canônico
percorre arestas compiladas, persiste bundle/eventos e retoma por identidade; com o
workflow `new-feature`, `harness run` seleciona a composição F7.C1; nos demais, o registry vazio
falha fechado antes de modelo ou tool. `PromotionManager` suporta
dry-run explícito sem atribuir ao resultado semântica de promoção. O `PythonAstIndexer` permanece
separado do lifecycle, mas
`harness index` agora resolve o commit Git real, lê seus blobs `.py`, produz símbolos AST e publica um
snapshot `ready` canônico. O `CodebaseMemoryAdapter` somente serve esse snapshot com digest válido;
consulta ausente/inválida continua falhando explicitamente, sem indexação implícita.

Na F4.4 promovida, `PLANNING → EXECUTING` somente ocorre depois de contexto suficiente relido,
structured output tipado, payload content-addressed, projeção `plan.json` atômica e evento
`PLAN_GENERATED`. Resume recupera o payload sem nova chamada; efeito iniciado sem outcome, tamper,
duplicata ou divergência de policy/input bloqueiam antes do primeiro nó.

## 4. Matriz de comandos

| Comando | Código existe | Efeito real comprovado | Classificação |
|---|---:|---:|---|
| `harness init` | Sim | Cria/copia scaffold local | Implementado como base |
| `harness doctor` | Sim | Inspeciona sete componentes em seis estágios, compartilha resultado texto/JSON e retorna não zero quando unhealthy | F6.4 `PROMOTED`; read-only real |
| `harness compile` | Sim | Compila pelo pipeline canônico e grava artefato validado | Implementado como contrato interno |
| `harness index` | Sim | Faz rebuild AST dos blobs Python do SHA Git atual, publica e recarrega snapshot íntegro | Implementado; explícito, Python-only e ainda fora do lifecycle |
| `harness run` | Sim | Para `new-feature`, compõe provider, tools e worktree; workflows não registrados falham antes do efeito | MVP público limitado / fail-closed |
| `harness status` | Sim | Projeta estado tipado, tentativa, duração, blocker, próxima ação e budget | F6.5 `PROMOTED`; leitura local fail-closed |
| `harness inspect` | Sim | Lê status, digests, journal e aprovação sem payload bruto | F6.5 `PROMOTED`; leitura local fail-closed |
| `harness approve` | Sim | Persiste decisão ligada ao conteúdo da solicitação corrente | F5.6 `PROMOTED`; não fabrica candidate nem retoma sem backend |
| `harness resume` | Sim | Retoma do bundle canônico | Implementado como contrato injetável |
| `harness verify` | Sim | Carrega worktree validado, resolve configuração/argv, persiste resultado commit-bound e executa targeted → full | F4.5–F4.8 `PROMOTED`; primitiva injetável |
| `harness audit` | Sim | Valida o evento canônico, falha fechado e exporta JSON/SARIF com identidade exata | F6.2 `PROMOTED`; tamper-evident local, com HMAC opcional por API |
| `harness rollback` | Sim | Executa `git revert --no-edit` do SHA canônico com trust, aprovação e conflito fail-closed | F5.7 `PROMOTED`; primitiva injetável, sem gates pós-reversão automáticos |

## 5. Riscos prioritários

| Prioridade | Risco | Causa atual | Fase responsável |
|---|---|---|---|
| Resolvido | Wiring público ausente | F7.C1 passou a compor o caminho `new-feature` e o comprovou pela wheel instalada | PR #92 + reconciliação #93 |
| Resolvido | Portabilidade do artefato | F7.4 certificou package resources, paths por SO e wheel externa em Windows/Linux | PR #90 + reconciliação #91 |
| P1 | Escopo de composição limitado | Somente `new-feature` compõe provider, tools, worktree, gates, promotion, knowledge e evidence | Limitação publicada da RC |
| P1 | Âncora somente local | Journal/evidence possuem hash e digest, mas não uma âncora externa imutável | Limitação publicada; fora do MVP distribuído |
| P2 | Gates pós-rollback ausentes | O revert é real e validado, mas a suíte não é reexecutada automaticamente depois dele | Limitação publicada da RC |
| P2 | Serviços live condicionais | Provider remoto e Serena MCP dependem de configuração, credenciais e disponibilidade externa | Doctor/configuração fail-closed; documentação de suporte F7.4 |

## 6. Gates para considerar o produto operacional

- instalação em ambiente limpo e em repositório externo;
- nenhum adapter simulado registrado no runtime;
- doctor falha quando dependência real estiver ausente;
- toda escrita ocorre dentro de worktree criado por Git;
- comando de ferramenta usa argv, allowlist, cwd confinado e `shell=False`;
- gate obrigatório não executado bloqueia;
- aprovação pausa e retoma após reinício;
- promoção produz candidate SHA e promoted SHA reais;
- rollback usa `git revert`; a ausência de gates pós-reversão é publicada e não recebe claim de sucesso integral;
- E2E público cobre sucesso, falha, retry, resume, promoção e rollback sem adapter simulado em produção;
- CI Windows/Linux e artefato de release validados.

Os critérios completos estão no
[plano de implementação](plano_implementacao_harness_operacional.md).
