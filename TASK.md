# TASK.md — AI Engineering Harness · Painel Operacional

> **Função:** estado corrente e retomada rápida. Histórico detalhado não pertence a este arquivo.
> Nunca marque uma tarefa como concluída sem executar seu aceite e comprovar o estado remoto observado.

## 1. Fontes de verdade

1. Este painel: fase, coordenação, tarefa ativa, bloqueios e próxima ação.
2. [Dossiê ativo](docs/tasks/active/F3.1.md): problema, evidência, escopo, aceite e rollback.
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
| **Tarefa ativa** | `F3.1` — implementar provider real de modelo |
| **Gate** | `READY`; contrato congelado antes do primeiro arquivo de implementação |
| **Executor ativo** | `Codex`, único escritor |
| **Workspace** | `C:\Users\walla\OneDrive\Desktop\ai-engineering-harness` |
| **Branch** | `task/f3.1-model-provider`, criada de `1d08602dab90edc7eb9f8a72509fa5548abd80e3` |
| **Última main comprovada** | `1d08602dab90edc7eb9f8a72509fa5548abd80e3`; run `31228310847`, 11/11 verde |
| **Python** | `C:\Users\walla\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe` — 3.12.13 |
| **uv** | `.\build\f0.6-tools\uv\bin\uv.exe` — 0.11.32; nenhuma dependência nova nesta tarefa |

## 4. Última promoção comprovada

| Evidência | Resultado |
|---|---|
| Tarefa anterior | `DOC-PROTOCOL-ALIGN`, agora `PROMOTED` e arquivada |
| PR | #19; head `01f47ec911868765cdd4e6b537bf2c58769a634c`; merge `1d08602dab90edc7eb9f8a72509fa5548abd80e3` |
| CI do PR | run `31228197660`, evento `pull_request`, 11/11 jobs verdes incluindo `CI required` |
| CI pós-merge | run `31228310847`, evento `push` em `main`, SHA do merge, 11/11 jobs verdes |
| Linha comprovada | `main == origin/main == 1d08602dab90edc7eb9f8a72509fa5548abd80e3` antes desta branch |

## 5. Tarefa ativa

Leia integralmente: [F3.1](docs/tasks/active/F3.1.md).

| Campo | Valor |
|---|---|
| **Objetivo** | substituir respostas fabricadas por provider remoto e local reais, tipados e fail-closed |
| **Escopo** | contratos/model adapters, testes determinísticos, teste live condicionado e documentação da tarefa |
| **Proibido** | roteamento F3.2, loop F3.3, outras tarefas/fases, dependências, lockfile e CI |
| **Estado local** | gate documental `READY`; implementação ainda não iniciada |
| **Estado remoto** | branch F3.1 ainda não publicada; nenhum PR/CI/merge antecipado |

## 6. Bloqueios atuais

Nenhum bloqueio ativo.

## 7. Próxima ação exata

```text
IMPLEMENTAR SOMENTE F3.1 A PARTIR DE checkpoint/f3.1-ready:
1. Implementar providers HTTP remoto/local, contratos tipados, falhas seguras e redaction do allowlist.
2. Executar aceite focado/negativo/live condicionado, compatibilidade, suíte integral e quality gates.
3. Revisar diff e escopo; registrar resultados reais no dossiê sem antecipar fatos remotos.
4. Publicar somente task/f3.1-model-provider e abrir seu único PR para main.
5. Nunca mesclar antes de todos os jobs, inclusive CI required, concluírem verdes e o PR estar sem conflitos.
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
