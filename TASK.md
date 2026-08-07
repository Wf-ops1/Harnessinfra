# TASK.md — AI Engineering Harness · Painel Operacional

> **Função:** estado corrente e retomada rápida. Histórico detalhado não pertence a este arquivo.
> Nunca marque uma tarefa como concluída sem executar seu aceite e comprovar o estado remoto observado.

## 1. Fontes de verdade

1. Este painel: fase, coordenação, tarefa ativa, bloqueios e próxima ação.
2. [Dossiê ativo](docs/tasks/active/DOC-PROTOCOL-ALIGN.md): problema, evidência, escopo, aceite e rollback.
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
| **Próxima fase** | Fase 3 — ainda não iniciada; bloqueada até promover `DOC-PROTOCOL-ALIGN` |
| **Tarefa ativa** | `DOC-PROTOCOL-ALIGN` — alinhar fontes normativas e ciclo de um PR |
| **Gate** | `READY`; somente governança documental/testes autorizados |
| **Executor ativo** | `Codex`, único escritor |
| **Workspace** | `C:\Users\walla\OneDrive\Desktop\ai-engineering-harness` |
| **Branch** | `docs/align-operational-protocol`, criada de `87373ec4ac91e2565e5f78b60bf2a669c121c381` |
| **Última main comprovada** | `87373ec4ac91e2565e5f78b60bf2a669c121c381`; run `31219589499`, 11/11 verde |
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
| Fechamento do ledger | PR #17; checks run `31218768354`, 11/11 verdes antes do merge |
| Promoção do fechamento | merge `ff2d9e5035423844e8098757e0c6a9f689e8cab1`; pós-merge `31218998232`, 11/11 verdes |
| Painel terminal | PR #18; merge `87373ec4ac91e2565e5f78b60bf2a669c121c381`; pós-merge `31219589499`, 11/11 verdes |
| Linha comprovada | `main == origin/main == 87373ec4ac91e2565e5f78b60bf2a669c121c381` antes desta branch |

## 5. Tarefa ativa

Leia integralmente: [DOC-PROTOCOL-ALIGN](docs/tasks/active/DOC-PROTOCOL-ALIGN.md).

| Campo | Valor |
|---|---|
| **Objetivo** | restaurar o contrato exato do gate e eliminar contradições de localização/ciclo |
| **Escopo** | plano, `AGENTS.md`, painel, dossiê ativo e teste estrutural |
| **Proibido** | produto, CI, dependências, dossiês históricos e qualquer implementação F3 |
| **Estado remoto** | branch/PR ainda não publicados; nenhum fato remoto antecipado |

## 6. Bloqueios atuais

Nenhum bloqueio ativo.

## 7. Próxima ação exata

```text
CONCLUIR SOMENTE DOC-PROTOCOL-ALIGN EM UM ÚNICO PR:
1. Restaurar no plano o contrato detalhado do dossiê/gate e alinhar a localização dos resultados.
2. Alinhar AGENTS ao ciclo de um PR e à certificação da promoção no gate seguinte.
3. Adicionar regressões que impeçam contradição, gate incompleto e PR recursivo de fechamento.
4. Executar aceite focado, suíte integral, qualidade e auditoria de escopo.
5. Publicar somente esta branch; aguardar todos os checks verdes; então mesclar e confirmar CI em main.
6. Não abrir PR de fechamento. Manter o dossiê `PROMOTION_PENDING` para certificação no primeiro
   commit do próximo gate; não iniciar F3 nesta execução.
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
