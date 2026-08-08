# TASK.md — AI Engineering Harness · Painel Operacional

> **Função:** estado corrente e retomada rápida. Histórico detalhado não pertence a este arquivo.
> Nunca marque uma tarefa como concluída sem executar seu aceite e comprovar o estado remoto observado.

## 1. Fontes de verdade

1. Este painel: fase, coordenação, tarefa ativa, bloqueios e próxima ação.
2. [Dossiê ativo](docs/tasks/active/F3.C1.md): problema, evidência, escopo, aceite e rollback.
3. [Plano principal](docs/plano_implementacao_harness_operacional.md): requisitos e dependências das fases.
4. [Regras dos agentes](.agents/AGENTS.md): protocolo obrigatório de execução e Git.
5. [Índice histórico](docs/tasks/README.md): dossiês concluídos, PRs, merges e runs.

Em conflito: pedido explícito do usuário → plano principal → regras dos agentes → painel/dossiê, que
devem ser corrigidos para refletir a decisão. Nunca depender somente do histórico da conversa.

## 2. Invariantes operacionais

- um único executor/escritor por vez;
- nenhuma implementação sem problema comprovado, escopo/aceite congelados e gate `READY`;
- uma branch e um PR por tarefa, sempre a partir de `main` sincronizada e verde;
- nenhum merge antes de todos os checks do PR, incluindo `CI required`, terminarem verdes;
- nenhuma tarefa seguinte antes do merge anterior e da CI pós-merge verde em `main`;
- sem mocks ou sucesso sintético em produção; integração indisponível falha explicitamente;
- paths e efeitos confinados; comandos futuros por `argv` e `shell=False`;
- secrets redigidos antes de persistência; estado necessário para retomar deve ser durável;
- histórico concluído fica nos dossiês e no Git, não é duplicado neste painel.

## 3. Estado atual

| Campo | Estado observado |
|---|---|
| **Fase concluída** | Fase 2 — F2.1–F2.6 implementadas e promovidas |
| **Fase ativa** | Fase 3 — realinhamento obrigatório antes de F3.4 (DEC-012) |
| **Tarefa ativa** | `F3.C1` — integridade de modelo e model-turn |
| **Gate** | `READY`; `COMPLETED_LOCAL / PROMOTION_PENDING` |
| **Executor ativo** | `Codex`, único escritor |
| **Workspace** | `C:\Users\walla\OneDrive\Desktop\ai-engineering-harness` |
| **Branch** | `task/f3.c1-model-turn-integrity`, criada de `0e64a88fbe1ca28b8da6a4598a4f4391ba916dd1` |
| **Última main comprovada** | `0e64a88fbe1ca28b8da6a4598a4f4391ba916dd1`; run `31232731611`, 11/11 verde |
| **Python** | `C:\Users\walla\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe` — 3.12.13 |
| **uv** | `.\build\f0.6-tools\uv\bin\uv.exe` — 0.11.32; nenhuma dependência nova autorizada |

## 4. Última promoção comprovada

| Evidência | Resultado |
|---|---|
| Tarefa anterior | `F3.3`, agora `PROMOTED` e arquivada no primeiro commit deste gate |
| PR | #22; head `e29f42eaf09373451b2e9858e78a15188fc3006f`; merge `0e64a88fbe1ca28b8da6a4598a4f4391ba916dd1` |
| CI do PR | run `31232616249`, evento `pull_request`, 11/11 jobs verdes incluindo `CI required` |
| CI pós-merge | run `31232731611`, evento `push` em `main`, SHA exato do merge, 11/11 jobs verdes |
| Linha comprovada | `main == origin/main == 0e64a88fbe1ca28b8da6a4598a4f4391ba916dd1` antes desta branch |

## 5. Tarefa ativa

Leia integralmente: [F3.C1](docs/tasks/active/F3.C1.md) e o
[realinhamento da Fase 3](docs/fase3_realignamento_operacional.md).

| Campo | Valor |
|---|---|
| **Objetivo** | corrigir continuação nativa, JSON/usage/cancelamento e preservar todos os model calls em sucesso, falha e journal |
| **Escopo** | provider/router, tool loop, metadata do node, replay compatível, documentação e testes focados |
| **Proibido** | dispatch/durabilidade/policy F3.C2, path/terminal/worktree/edição F3.4–F3.8, dependências e CI |
| **Estado local** | implementação `8bd0caa`; `527 passed, 1 skipped, 6 subtests`; quality, package e escopo verdes |
| **Estado remoto** | branch F3.C1 ainda não publicada; nenhum PR/CI/merge antecipado |

## 6. Bloqueios atuais

Nenhum bloqueio ativo. Merge continua proibido até todos os jobs do PR estarem concluídos com
`success` e o PR permanecer sem conflitos.

## 7. Próxima ação exata

```text
EXECUTAR SOMENTE F3.C1:
1. Registrar o fechamento local e `checkpoint/f3.c1-complete`; repetir documentação/diff/scope.
2. Revisar o diff final e publicar o único PR F3.C1.
3. Inspecionar todos os jobs; merge proibido com check pendente/ausente/ignorado/falho ou conflito.
4. Com 100% verde, fazer merge commit; aguardar CI push em main no SHA exato e sincronizar main.
5. PAUSAR. F3.C2 exige nova autorização explícita do usuário; não avançar automaticamente.
```

## 8. Retomada após perda de contexto

1. Leia este arquivo integralmente.
2. Leia o dossiê ativo indicado na seção 5, quando houver.
3. Leia a fase relevante no plano principal.
4. Confirme `.git`, branch, `git status --short --branch`, `git log -10` e upstream.
5. Confirme no GitHub o último merge e a CI pós-merge do SHA registrado.
6. Execute somente a próxima ação exata; se escopo/estado divergir, pare e recongele o dossiê.

## 9. Regras de manutenção

- limite máximo: 300 linhas;
- não copiar dossiê concluído, logs extensos, contratos completos ou histórico de fases para o painel;
- resultados, arquivos, comandos e rollback detalhados ficam no dossiê ativo;
- após promoção, arquivar o dossiê em `docs/tasks/completed/` e atualizar o índice;
- correção de dossiê concluído exige mudança documental explícita; nunca reescrever evidência silenciosamente;
- entre tarefas, `active/` pode conter somente seu README e o painel deve apontar `nenhuma tarefa ativa`;
- PR, CI, merge ou SHA só são registrados depois de observados.

---

*Atualizado em: 2026-08-08 | Fonte normativa: plano principal + DEC-012*
