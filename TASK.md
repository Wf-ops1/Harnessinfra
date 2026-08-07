# TASK.md — AI Engineering Harness · Painel Operacional

> **Função:** estado corrente e retomada rápida. Histórico detalhado não pertence a este arquivo.
> Nunca marque uma tarefa como concluída sem executar seu aceite e comprovar o estado remoto observado.

## 1. Fontes de verdade

1. Este painel: fase, coordenação, tarefa ativa, bloqueios e próxima ação.
2. Dossiê ativo em `docs/tasks/active/`, quando apontado pela seção 5; neste momento não há nenhum.
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
| **Próxima fase** | Fase 3 — ainda não iniciada; auditar dependências e selecionar uma única primeira tarefa |
| **Tarefa ativa** | nenhuma tarefa ativa; somente o fechamento documental desta promoção está em trânsito |
| **Gate** | nenhum gate de implementação aberto; F3 permanece sem autorização de código |
| **Executor ativo** | `Codex`, somente como escritor do fechamento documental |
| **Workspace** | `C:\Users\walla\OneDrive\Desktop\ai-engineering-harness` |
| **Branch** | `docs/close-task-ledger-refactor`, criada de `fafbf627804f1a2a23d988c06dd123a3eee01348` |
| **Git baseline** | `main == origin/main == fafbf627804f1a2a23d988c06dd123a3eee01348`; CI pós-merge verde |
| **Python** | `C:\Users\walla\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe` — 3.12.13 |
| **uv** | `.\build\f0.6-tools\uv\bin\uv.exe` — 0.11.32; nenhuma dependência nova nesta tarefa |

## 4. Última promoção comprovada

| Evidência | Resultado |
|---|---|
| Implementação F2.6 | PR #14; merge `2dac824684b541c0b3ae4d6caf08ec9161524d91` |
| CI F2.6 | PR run `31214724386` e pós-merge `31215162155`, 11/11 verdes |
| Fechamento F2 | PR #15; merge `d48151b752aa373756c46bfee58932fa5abf4bf5` |
| CI do fechamento | PR run `31215674969`; pós-merge run `31215944126`, evento `push` em `main`, 11/11 verdes |
| Refatoração do ledger | PR #16; checks run `31218206768`, 11/11 verdes antes do merge |
| Promoção do ledger | merge `fafbf627804f1a2a23d988c06dd123a3eee01348`; pós-merge `31218399437`, 11/11 verdes |
| Linha oficial | `main == origin/main == fafbf627804f1a2a23d988c06dd123a3eee01348` antes desta branch |

## 5. Tarefa ativa

Nenhuma tarefa ativa. O dossiê `DOC-TASK-LEDGER` foi promovido e está arquivado em
[`docs/tasks/completed/DOC-TASK-LEDGER.md`](docs/tasks/completed/DOC-TASK-LEDGER.md).

| Campo | Valor |
|---|---|
| **Última tarefa** | `DOC-TASK-LEDGER` — `COMPLETED E PROMOVIDA` |
| **Fechamento atual** | registrar evidência observada e esvaziar `active/`; nenhuma mudança de produto |
| **Próxima autorização possível** | auditar Fase 3 e congelar um novo dossiê `READY` em nova branch, após este fechamento |

## 6. Bloqueios atuais

Nenhum bloqueio ativo.

## 7. Próxima ação exata

```text
FECHAR SOMENTE DOC-TASK-LEDGER:
1. Validar painel sem tarefa ativa, dossiê arquivado, índice, encoding, links e integridade histórica.
2. Publicar somente esta branch de fechamento e abrir PR documental; não publicar nem apagar tags.
3. Aguardar todos os checks pré-merge verdes; somente então executar merge commit autorizado.
4. Confirmar CI pós-merge verde em main, sincronizar o checkout e parar.
5. Na próxima execução autorizada, auditar a ordem da Fase 3 — incluindo F3.6 antes de F3.1–F3.3 —
   e congelar uma única primeira tarefa antes de qualquer código.
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

*Atualizado em: 2026-08-07 | Fonte normativa: `docs/plano_implementacao_harness_operacional.md`*
