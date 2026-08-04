# Handoff operacional — Fase 1

> Documento de retomada para iniciar a Fase 1 sem depender do histórico de uma conversa.
> O agente deve verificar o snapshot abaixo; não deve aceitá-lo cegamente.

## 1. Objetivo deste handoff

Entregar a um novo executor o estado confirmado após a Fase 0 e impor uma fronteira segura para a
F1.1. A primeira execução da nova conversa deve auditar e preparar o gate de defensabilidade. Nenhum
arquivo de implementação da F1 pode ser alterado antes desse gate estar completo e marcado `READY`.

## 2. Fontes de verdade e precedência

Ler integralmente, nesta ordem operacional:

1. `.agents/AGENTS.md` — regras obrigatórias dos agentes;
2. `TASK.md` — fase, checkpoint, bloqueios, executor e próxima ação;
3. `docs/plano_implementacao_harness_operacional.md`, seção **Fase 1 / F1.1** — requisitos e aceite;
4. este handoff — snapshot verificável e roteiro de retomada.

Em conflito, prevalecem: pedido explícito do usuário, plano operacional e, por fim, o estado que deve
ser corrigido em `TASK.md`.

## 3. Snapshot confirmado em 2026-08-04

| Campo | Estado esperado |
|---|---|
| Repositório | `https://github.com/Wf-ops1/Harnessinfra.git` |
| Branch ativa | `main` |
| HEAD local/remoto | `1aaaba8dfe88ee500d31d1138823d5704a04521e` |
| Worktree | limpa; `main...origin/main` |
| Checkpoint local da Fase 0 | `checkpoint/f0.6-complete` |
| Commit do checkpoint | `fd4de2c119daf9a401f450a907f1d07bf3f580e9`; deve ser ancestral de `main` |
| Tags remotas | nenhuma; o checkpoint não foi publicado |
| Proteção de `main` | `CI required`, `strict=true`, `enforce_admins=true`; force-push e exclusão desabilitados |
| PR de promoção | [#1](https://github.com/Wf-ops1/Harnessinfra/pull/1), mesclado em `3f29c4c894808eb47464c96a01c9048198d971c9` |
| Prova de bloqueio | [#2](https://github.com/Wf-ops1/Harnessinfra/pull/2), fechado sem merge após falha controlada e revert |
| PR do registro | [#3](https://github.com/Wf-ops1/Harnessinfra/pull/3), mesclado em `1aaaba8dfe88ee500d31d1138823d5704a04521e` |
| CI final de `main` | [run 30917657879](https://github.com/Wf-ops1/Harnessinfra/actions/runs/30917657879), `completed/success`, 11/11 jobs |
| Estado de F1.1 | `pending`; nenhum código da Fase 1 autorizado |

Se qualquer item divergir, interromper a implementação, investigar e alinhar `TASK.md` antes de
preparar a F1.1.

## 4. O que a Fase 0 entregou

- ambiente reproduzível com `uv.lock` e Python `>=3.11,<3.15`;
- testes, mypy, Ruff, compileall, build e smoke isolado da wheel;
- package version centralizada e namespaces de versão separados;
- documentação sem alegações operacionais falsas;
- GitHub Actions em Windows/Linux com aggregate fail-closed `CI required`;
- proteção real de `main`, inclusive para administradores;
- prova remota de que check vermelho bloqueia merge e revert verde restaura o estado.

A Fase 0 **não** transformou o projeto em infraestrutura operacional. Providers, Serena,
Codebase-Memory, worktrees, promoção, recovery e doctor continuam experimentais, simulados ou
planejados conforme README e auditorias.

## 5. Primeira tarefa concreta: F1.1

**F1.1 — Definir schema tipado do grafo.**

O plano exige modelos Pydantic para:

- `GraphSpec`;
- `GraphMetadata`;
- `NodeSpec`;
- `AgentNodeSpec`;
- `DeterministicNodeSpec`;
- `HumanApprovalNodeSpec`;
- `TerminalStateSpec`;
- `RetryPolicySpec`;
- `ToolPermissionSpec`;
- `CompiledGraphArtifact`.

Regras que o futuro contrato deve validar:

- IDs únicos;
- entrypoint existente;
- arestas apontando apenas para nó ou terminal existente;
- pelo menos um terminal de sucesso e um de falha;
- nenhum nó inalcançável;
- nenhuma aresta implícita;
- ciclos somente com `retry_policy` explícita;
- `max_iterations > 0` e condição de saída obrigatória;
- tipo do executor compatível com os campos do nó.

Esses requisitos são alvos do plano, não prova de que a implementação atual esteja ausente ou
incorreta. A auditoria deve comparar requisito e código antes de propor alterações.

## 6. Superfícies obrigatórias da auditoria F1.1

Inspecionar pelo menos:

- `src/ai_engineering_harness/contracts/`;
- `src/ai_engineering_harness/compiler/`;
- `compiler/` — caminho legado/duplicado, sem tratá-lo como fonte oficial;
- `src/ai_engineering_harness/defaults/graphs/`;
- `src/ai_engineering_harness/versioning.py`;
- testes de contratos, compilador, versionamento e ciclo completo;
- imports públicos e consumidores dos modelos existentes.

Para cada problema alegado, registrar:

1. comando executado;
2. saída observada;
3. arquivo e símbolo envolvidos;
4. comportamento atual;
5. comportamento exigido pelo plano;
6. risco de compatibilidade;
7. teste capaz de provar correção e falha segura.

## 7. Gate obrigatório antes da implementação

O dossiê da F1.1 em `TASK.md` deve conter:

- `problem_statement` comprovado;
- evidências reproduzíveis;
- branch, HEAD e baseline limpo;
- executor ativo;
- escopo permitido por arquivo/símbolo;
- escopo explicitamente proibido;
- decisões de contrato congeladas;
- critérios de aceite positivos e negativos;
- estratégia de compatibilidade/migração;
- comandos de teste focados e regressão integral;
- checkpoint Git anterior ao primeiro arquivo de implementação;
- triggers e procedimento de rollback;
- fronteira externa: nenhum push, PR, merge, tag remota ou mudança de proteção sem autorização.

Criar uma branch da Fase 1 a partir de `main` somente depois de confirmar o snapshot. Alterações para
preparar o próprio dossiê são permitidas; alterações de Python, YAML de produção ou schema não são.

## 8. Saída esperada da primeira execução

A primeira execução no novo chat termina com:

- auditoria do snapshot Git/CI;
- mapa concreto dos contratos e compiladores existentes;
- primeira lacuna comprovada da F1.1;
- lista exata de arquivos potencialmente alteráveis;
- critérios congelados e rollback;
- branch/checkpoint preparados;
- `TASK.md` atualizado;
- confirmação explícita de que nenhum código da F1.1 foi implementado.

## 9. Prompt para copiar no novo chat

```text
Você será o executor principal da Fase 1 deste projeto.

Não use o histórico de outra conversa como fonte de verdade. Antes de alterar qualquer arquivo:

1. Leia integralmente .agents/AGENTS.md.
2. Leia TASK.md, especialmente Fase Atual, último checkpoint, próxima ação e protocolo de defensabilidade.
3. Leia integralmente docs/handoff_fase_1.md.
4. Leia a seção Fase 1/F1.1 de docs/plano_implementacao_harness_operacional.md.
5. Confirme branch, HEAD, upstream, remote, worktree, tags locais/remotas, checkpoint, proteção de main e CI final.
6. Se o estado divergir do handoff, não implemente: investigue e alinhe TASK.md primeiro.
7. Audite schemas, contratos, grafos e os dois caminhos de compilação existentes com comandos e arquivos concretos.
8. Não altere Python, YAML de produção ou schemas antes de criar o gate de defensabilidade da F1.1.
9. Registre no TASK.md: problema comprovado, evidências, baseline, escopo permitido/proibido, decisões congeladas, aceite, testes, checkpoint e rollback.
10. Não faça push, PR, merge, tag remota ou alteração de proteção sem autorização explícita.
11. Nesta primeira execução, pare antes do primeiro arquivo de implementação.

Entregue: diagnóstico concreto, primeira lacuna comprovada, arquivos em escopo, aceite, rollback, branch/checkpoint e confirmação de que F1.1 continua sem implementação.
```

## 10. Regra de manutenção

Atualizar este handoff somente em fronteiras de fase ou quando branch, checkpoint, CI obrigatória ou
próxima tarefa mudarem. O estado operacional corrente continua pertencendo ao `TASK.md`.
