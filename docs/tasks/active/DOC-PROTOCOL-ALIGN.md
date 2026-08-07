# DOC-PROTOCOL-ALIGN — Alinhar o protocolo operacional

> **Gate:** `READY`
> **Executor:** `Codex`
> **Autorizado em:** `2026-08-07T20:36:12-03:00`
> **Fronteira:** governança documental anterior à Fase 3; nenhum código de produto ou tarefa F3.

## Problema comprovado

| Evidência | Resultado observado |
|---|---|
| `docs/plano_implementacao_harness_operacional.md:57` | manda gravar resultado, arquivos, comandos e rollback no `TASK.md` |
| `.agents/AGENTS.md:26` e `:86` | manda manter o `TASK.md` curto e gravar detalhes no dossiê ativo |
| `git show d48151b:TASK.md`, seções 4.1.1–4.1.4 | contrato detalhado exigia baseline, escopo/aceite congelados, rollback, responsabilidade, `BLOCKED/READY` e proibição de enfraquecimento |
| busca nas fontes normativas atuais | o contrato detalhado não existe integralmente em `TASK.md`, `AGENTS.md` ou no plano; somente exemplos históricos permanecem nos dossiês concluídos |
| plano `:59`, `AGENTS.md:40` e PRs #16–#18 | a regra de um PR por tarefa permaneceu normativa, mas `DOC-TASK-LEDGER` gerou três PRs de fechamento |
| `TASK.md:40`, Git e CI | painel registra `ff2d9e5`, enquanto `main == origin/main == 87373ec4` e a CI `31219589499` já foi comprovada verde |

## Baseline conhecido

```yaml
baseline:
  branch: "docs/align-operational-protocol"
  base_commit: "87373ec4ac91e2565e5f78b60bf2a669c121c381"
  status: "clean; main == origin/main antes da criação da branch"
  upstream_ci:
    run: "31219589499"
    event: "push"
    branch: "main"
    commit: "87373ec4ac91e2565e5f78b60bf2a669c121c381"
    result: "4 quality + 4 tests + 2 package + CI required = success"
  python: "3.12.13"
  uv: "build/f0.6-tools/uv/bin/uv.exe 0.11.32"
```

## Decisão congelada

1. O plano principal, fonte normativa superior, receberá o contrato completo do dossiê e do gate
   `READY`; `AGENTS.md` manterá o resumo operacional e apontará para esse contrato.
2. `TASK.md` continuará como painel curto. Resultado detalhado, arquivos, comandos, decisões e rollback
   ficam no dossiê; o painel mantém apenas estado, bloqueios, última promoção e próxima ação.
3. O gate começa `BLOCKED` e só muda para `READY` quando problema, evidência, baseline, escopo,
   aceite, rollback, executor e horário estiverem completos. Critério falho nunca pode ser removido,
   ignorado ou enfraquecido.
4. Cada tarefa terá uma branch e um PR. Gate, implementação, validação e estado local final pertencem
   a esse mesmo PR; não haverá PR recursivo de fechamento.
5. Como um commit não pode provar seu próprio merge futuro, o primeiro commit da tarefa seguinte deve
   observar e registrar PR, checks, merge e CI pós-merge da tarefa anterior, atualizar seu dossiê para
   `PROMOTED`, arquivá-lo e então criar o novo dossiê ativo `READY`. Isso é pré-requisito do novo gate,
   não um segundo PR da tarefa anterior.
6. Até a certificação seguinte, o dossiê localmente concluído permanece em `active/` com estado
   `COMPLETED_LOCAL / PROMOTION_PENDING`; não autoriza nova implementação.
7. Os PRs #17 e #18 serão registrados como desvio histórico não precedente. Nenhuma regra de CI,
   autorização ou proteção foi enfraquecida: todos os merges ocorreram após checks verdes.
8. Testes estruturais impedirão nova divergência entre plano, `AGENTS.md` e painel.

## Escopo congelado

### Permitido

- `TASK.md` — estado corrente, gate, baseline e próxima ação desta tarefa;
- `.agents/AGENTS.md` — localização dos detalhes, contrato do gate e fechamento não recursivo;
- `docs/plano_implementacao_harness_operacional.md` — contrato normativo e correção do passo 6;
- `docs/tasks/active/DOC-PROTOCOL-ALIGN.md` — dossiê desta tarefa;
- `tests/unit/test_task_ledger.py` — regressões de consistência e ciclo de vida.

### Proibido

- `src/`, `compiler/`, `.github/`, `README.md`, `pyproject.toml`, `uv.lock` e dependências;
- iniciar F3.1–F3.8, criar worktree de execução, provider ou tool real;
- alterar critérios funcionais das fases ou as 12 invariantes de implementação;
- mais de uma branch/PR para esta tarefa, PR de fechamento, tag remota, force-push ou bypass;
- reescrever dossiês concluídos ou payloads cobertos pelo manifesto de migração.

## Critérios de aceite congelados

```yaml
acceptance:
  normative_alignment:
    command: >-
      inspecionar plano, AGENTS e TASK; executar tests/unit/test_task_ledger.py
    expected: >-
      plano e AGENTS concordam sobre painel curto, dossiê detalhado, campos obrigatórios,
      BLOCKED/READY, não enfraquecimento, um PR e certificação no gate seguinte
  historical_integrity:
    command: >-
      python -m pytest tests/unit/test_task_ledger.py tests/unit/test_documentation.py
      tests/unit/test_encoding.py -q
    expected: "12 ou mais testes e 6 subtests verdes; 19 payloads legados com SHA-256 íntegro"
  regression:
    command: "python -m pytest tests/unit tests/e2e -q"
    expected: "suíte integral verde, sem skip/xfail novo"
  quality:
    command: >-
      python -m mypy src; python -m ruff check .;
      python -m compileall -q src compiler tests; uv lock --check; git diff --check
    expected: "todos exit 0"
  scope:
    command: "auditar git diff desde checkpoint/doc-protocol-align-ready"
    expected: "somente os cinco paths permitidos; zero diff nos paths proibidos"
```

## Rollback

### Gatilhos

- alguma regra anterior for removida ou enfraquecida em vez de relocalizada;
- o plano e `AGENTS.md` continuarem contraditórios;
- o ciclo exigir mais de um PR para concluir uma tarefa;
- algum teste histórico, documental, funcional ou de qualidade falhar;
- qualquer path proibido mudar ou a solução antecipar a Fase 3.

### Procedimento

Antes de commit, inverter somente os hunks desta tarefa com `apply_patch`. Depois de commit, usar
`git revert` nos commits exclusivos de `DOC-PROTOCOL-ALIGN`. Nunca usar reset destrutivo, apagar
evidência ou sobrescrever trabalho preexistente.

### Verificação pós-rollback

Confirmar `main == origin/main == 87373ec4`, worktree limpa, zero diff nos paths proibidos e repetir
os testes documentais/estruturais do baseline.

## Checklist de liberação

```text
[x] contradições e perda normativa comprovadas por arquivo/linha
[x] baseline Git e CI pós-merge verdes comprovados
[x] escopo, fronteira F3 e efeitos permitidos congelados
[x] critérios de alinhamento, integridade, regressão, qualidade e escopo congelados
[x] ciclo de um PR e certificação não recursiva definidos
[x] rollback não destrutivo definido
[x] executor e horário registrados
```
