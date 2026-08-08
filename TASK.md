# TASK.md — AI Engineering Harness · Painel Operacional

> **Função:** estado corrente e retomada rápida. Histórico detalhado não pertence a este arquivo.
> Nunca marque uma tarefa como concluída sem executar seu aceite e comprovar o estado remoto observado.

## 1. Fontes de verdade

1. Este painel: fase, coordenação, tarefa ativa, bloqueios e próxima ação.
2. [Dossiê ativo](docs/tasks/active/F3.C2.md): problema, evidência, escopo, aceite e rollback.
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
| **Tarefa ativa** | `F3.C2` — execução durável de tools e policy |
| **Gate** | `READY`; `COMPLETED_LOCAL / PROMOTION_PENDING` |
| **Executor ativo** | `Codex`, único escritor |
| **Workspace** | `C:\Users\walla\OneDrive\Desktop\ai-engineering-harness` |
| **Branch** | `task/f3.c2-tool-effect-durability`, criada de `5616fc548716acb3561dd67d3905eb008130b58c` |
| **Última main comprovada** | `5616fc548716acb3561dd67d3905eb008130b58c`; run `31240455344`, 11/11 verde |
| **Python** | `C:\Users\walla\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe` — 3.12.13 |
| **uv** | `.\build\f0.6-tools\uv\bin\uv.exe` — 0.11.32; nenhuma dependência nova autorizada |

## 4. Última promoção comprovada

| Evidência | Resultado |
|---|---|
| Tarefa anterior | `F3.C1`, agora `PROMOTED` e arquivada neste primeiro commit do gate F3.C2 |
| PR | #23; head `78a0099a3909c40e1df6b692a841e6441bccf5a3`; merge `5616fc548716acb3561dd67d3905eb008130b58c` |
| CI do PR | run `31240274131`, evento `pull_request`, 11/11 jobs verdes incluindo `CI required` |
| CI pós-merge | run `31240455344`, evento `push` em `main`, SHA exato do merge, 11/11 jobs verdes |
| Linha comprovada | `main == origin/main == 5616fc548716acb3561dd67d3905eb008130b58c` antes desta branch |

## 5. Tarefa ativa

Leia integralmente: [F3.C2](docs/tasks/active/F3.C2.md) e o
[realinhamento da Fase 3](docs/fase3_realignamento_operacional.md).

F3.C2 exige nova autorização explícita; essa pausa foi cumprida e a autorização foi observada em
`2026-08-08T02:02:32-03:00`. Ela não autoriza F3.4 nem efeitos fora do dossiê congelado.

| Campo | Valor |
|---|---|
| **Objetivo** | gravar tool call antes do dispatch, persistir outcome depois do efeito e bloquear retomada ambígua sem reexecução |
| **Escopo** | tool loop/router, recorder sob lock/fencing, policy no dispatch, replay, documentação e testes focados |
| **Proibido** | path guard, terminal, worktree, promoção e edição F3.4–F3.8; dependências, schemas, adapters e CI |
| **Estado local** | implementação e todos os gates congelados verdes; commits locais `8187158` e `93e6a03`; fechamento documental/tag complete neste checkpoint |
| **Estado remoto** | PR [#24](https://github.com/Wf-ops1/Harnessinfra/pull/24) aberto contra `main`; run inicial `31242452446` enfileirado; merge não autorizado |

## 6. Bloqueios atuais

Não há implementação ativa. Branch e PR #24 foram publicados com autorização; os checks do head final
devem ficar integralmente verdes antes de pedir autorização de merge. F3.4 continua bloqueada.

## 7. Próxima ação exata

```text
PAUSAR EM `COMPLETED_LOCAL / PROMOTION_PENDING`:
1. Publicar esta reconciliação no mesmo PR #24 e observar todos os checks do novo head.
2. Não executar merge sem autorização explícita própria depois da CI verde.
3. Após merge autorizado, validar CI de `push` no SHA exato de `main` e sincronizar o repositório.
4. F3.4 exige promoção completa da F3.C2 e nova autorização explícita; não avançar automaticamente.
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
