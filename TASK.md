# TASK.md — AI Engineering Harness · Painel Operacional

> **Função:** estado corrente e retomada rápida. Histórico detalhado não pertence a este arquivo.
> Nunca marque uma tarefa como concluída sem executar seu aceite e comprovar o estado remoto observado.

## 1. Fontes de verdade

1. Este painel: fase, coordenação, tarefa ativa, bloqueios e próxima ação.
2. [Dossiê ativo](docs/tasks/active/F3.3.md): problema, evidência, escopo, aceite e rollback.
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
| **Fase ativa** | Fase 3 — modelos, ferramentas e workspace reais |
| **Tarefa ativa** | `F3.3` — loop de tool calls |
| **Gate** | `READY`; contrato congelado antes do primeiro arquivo de implementação |
| **Executor ativo** | `Codex`, único escritor |
| **Workspace** | `C:\Users\walla\OneDrive\Desktop\ai-engineering-harness` |
| **Branch** | `task/f3.3-tool-loop`, criada de `3956f16fb3046e1eb3721d76f544d6502329cb29` |
| **Última main comprovada** | `3956f16fb3046e1eb3721d76f544d6502329cb29`; run `31231730863`, 11/11 verde |
| **Python** | `C:\Users\walla\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe` — 3.12.13 |
| **uv** | `.\build\f0.6-tools\uv\bin\uv.exe` — 0.11.32; nenhuma dependência nova nesta tarefa |

## 4. Última promoção comprovada

| Evidência | Resultado |
|---|---|
| Tarefa anterior | `F3.2`, agora `PROMOTED` e arquivada |
| PR | #21; head `cd1cb7bf4220fd5dd8b05d338b915994f70fcb2b`; merge `3956f16fb3046e1eb3721d76f544d6502329cb29` |
| CI do PR | run `31231598253`, evento `pull_request`, 11/11 jobs verdes incluindo `CI required` |
| CI pós-merge | run `31231730863`, evento `push` em `main`, SHA do merge, 11/11 jobs verdes |
| Linha comprovada | `main == origin/main == 3956f16fb3046e1eb3721d76f544d6502329cb29` antes desta branch |

## 5. Tarefa ativa

Leia integralmente: [F3.3](docs/tasks/active/F3.3.md).

| Campo | Valor |
|---|---|
| **Objetivo** | executar tool calls autorizadas em loop limitado, devolver resultados ao modelo e persistir evidência redigida |
| **Escopo** | policy compilada, schemas/registry do ToolRouter, loop, budget/cancelamento e tool events/replay |
| **Proibido** | adapters reais novos, path guard/terminal/worktree/edição F3.4–F3.8, transports, dependências e CI |
| **Estado local** | gate documental `READY`; implementação ainda não iniciada |
| **Estado remoto** | branch F3.3 ainda não publicada; nenhum PR/CI/merge antecipado |

## 6. Bloqueios atuais

Nenhum bloqueio ativo.

## 7. Próxima ação exata

```text
IMPLEMENTAR SOMENTE F3.3 A PARTIR DE checkpoint/f3.3-ready:
1. Extrair a allowlist exclusivamente da política efetiva compilada do node.
2. Registrar schemas/handlers operacionais explícitos e validar todo o lote antes do primeiro efeito.
3. Executar o loop limitado, budgetado e cancelável; devolver resultados canônicos ao modelo.
4. Persistir tool records redigidos em pares de eventos e validar sua sequência no replay.
5. Executar focais, negativos, journal/replay, compatibilidade, suíte integral e quality gates.
6. Revisar escopo/diff, registrar evidências e publicar o único PR F3.3.
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
