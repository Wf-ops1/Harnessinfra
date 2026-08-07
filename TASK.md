# TASK.md — AI Engineering Harness · Painel Operacional

> **Função:** estado corrente e retomada rápida. Histórico detalhado não pertence a este arquivo.
> Nunca marque uma tarefa como concluída sem executar seu aceite e comprovar o estado remoto observado.

## 1. Fontes de verdade

1. Este painel: fase, coordenação, tarefa ativa, bloqueios e próxima ação.
2. [Dossiê ativo](docs/tasks/active/DOC-TASK-LEDGER.md): evidência, escopo, aceite e rollback da tarefa.
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
| **Próxima fase** | Fase 3 — ainda não iniciada; ordem de dependências deve ser auditada antes do primeiro gate |
| **Tarefa ativa** | `DOC-TASK-LEDGER` — refatoração documental anterior à Fase 3 |
| **Gate** | `READY`; recongelamento de encoding `checkpoint/docs-task-ledger-r2-ready` em `8db6120` |
| **Executor ativo** | `Codex`, único escritor |
| **Workspace** | `C:\Users\walla\OneDrive\Desktop\ai-engineering-harness` |
| **Branch** | `docs/refactor-task-ledger`, criada de `d48151b752aa373756c46bfee58932fa5abf4bf5` |
| **Git baseline** | `main == origin/main == d48151b752aa373756c46bfee58932fa5abf4bf5`; worktree limpa antes do gate |
| **Python** | `C:\Users\walla\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe` — 3.12.13 |
| **uv** | `.\build\f0.6-tools\uv\bin\uv.exe` — 0.11.32; nenhuma dependência nova nesta tarefa |

## 4. Última promoção comprovada

| Evidência | Resultado |
|---|---|
| Implementação F2.6 | PR #14; merge `2dac824684b541c0b3ae4d6caf08ec9161524d91` |
| CI F2.6 | PR run `31214724386` e pós-merge `31215162155`, 11/11 verdes |
| Fechamento F2 | PR #15; merge `d48151b752aa373756c46bfee58932fa5abf4bf5` |
| CI do fechamento | PR run `31215674969`; pós-merge run `31215944126`, evento `push` em `main`, 11/11 verdes |
| Linha oficial | `main == origin/main == d48151b752aa373756c46bfee58932fa5abf4bf5` antes desta branch |

## 5. Tarefa ativa

Leia integralmente: [DOC-TASK-LEDGER](docs/tasks/active/DOC-TASK-LEDGER.md).

| Campo | Valor |
|---|---|
| **Objetivo** | Separar painel corrente e dossiês históricos sem perda de evidência |
| **Escopo** | `TASK.md`, `.agents/AGENTS.md`, `docs/tasks/**` e testes documentais/estruturais congelados |
| **Proibido** | Produto, CI, dependências, plano principal, README e qualquer implementação F3 |
| **Estado local** | `COMPLETED LOCALMENTE`; 450 testes + 6 subtestes e todos os gates de qualidade/escopo verdes |
| **Estado remoto** | branch/PR ainda não publicados; nenhum fato remoto antecipado |

## 6. Bloqueios atuais

Nenhum bloqueio ativo.

## 7. Próxima ação exata

```text
CONCLUIR SOMENTE DOC-TASK-LEDGER:
1. Publicar somente esta branch e abrir um PR documental para main; não publicar tags.
2. Aguardar todos os checks pré-merge verdes; somente então executar merge commit autorizado.
3. Confirmar CI pós-merge verde em main e fechar o registro antes de iniciar qualquer tarefa F3.
```

## 8. Retomada após perda de contexto

1. Leia este arquivo integralmente.
2. Leia o dossiê ativo indicado na seção 5.
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

*Atualizado em: 2026-08-07 | Fonte normativa: `docs/plano_implementacao_harness_operacional.md`*
