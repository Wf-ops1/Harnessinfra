# DOC-TASK-LEDGER — Refatorar o painel e o arquivo de dossiês

> **Gate:** `READY`  
> **Executor:** `Codex`  
> **Autorizado em:** `2026-08-07T17:40:37-03:00`  
> **Fronteira:** tarefa documental anterior à Fase 3; nenhum código, provider, tool ou worktree F3.

## Problema comprovado

O `TASK.md` deixou de ser somente o painel de estado atual e passou a acumular protocolo global,
coordenação, dossiê ativo, dossiês completos de F0–F2 e histórico remoto. Isso torna obrigatória a
leitura repetida de quase cinco mil linhas para descobrir poucos campos operacionais correntes.

| Evidência | Resultado observado |
|---|---|
| `Get-Item TASK.md` e contagem UTF-8 | `377092` bytes e `4937` linhas no baseline |
| `git log --format=%H -- TASK.md` | `56` commits tocaram o painel |
| Busca de headings/dossiês | `18` headings de tarefa, `42` marcadores de dossiê e `21` blocos de rollback |
| Comparação documental | plano principal: `1800` linhas; `AGENTS.md`: `76`; README: `129` |
| Regra atual | `AGENTS.md` exige leitura integral do `TASK.md`, embora defina seu papel como estado, bloqueios, executor e próxima ação |
| Teste documental | `test_documentation.py` usa `docs.glob("*.md")` e não validaria arquivos Markdown em `docs/tasks/**` |

O snapshot fonte desta migração é `TASK.md` no commit
`d48151b752aa373756c46bfee58932fa5abf4bf5`. O checkout Windows com CRLF possui SHA-256
`0c7c68db691a93358b9a892916fe0b74601630a0b9caa7c9d6bf4e8808fa18ae`; o blob canônico entregue por
`git show d48151b:TASK.md`, normalizado em LF e usado pelo migrador, possui SHA-256
`f0f1a18751c0e730f7e6c4b6335192e0a655e06bba88e6996f9419270112d309`.

## Baseline comprovado

```yaml
baseline:
  branch: "docs/refactor-task-ledger"
  head: "d48151b752aa373756c46bfee58932fa5abf4bf5"
  status: "clean; main == origin/main no momento da criação"
  upstream_ci:
    run: "31215944126"
    event: "push"
    branch: "main"
    commit: "d48151b752aa373756c46bfee58932fa5abf4bf5"
    result: "4 quality + 4 tests + 2 package + CI required = success"
  python_command: "C:/Users/walla/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"
  uv_command: "build/f0.6-tools/uv/bin/uv.exe"
```

## Arquitetura congelada

1. `TASK.md` será o único painel operacional corrente e terá no máximo 300 linhas.
2. O painel conterá somente: fonte de verdade, invariantes resumidos, fase/coordenação atual, última
   promoção comprovada, tarefa ativa, bloqueios, próxima ação e retomada curta.
3. `docs/tasks/README.md` será o índice humano de tarefas e promoções, sem repetir dossiês.
4. `docs/tasks/active/` conterá no máximo um dossiê ativo; entre tarefas poderá conter somente um README.
5. `docs/tasks/completed/<ID>.md` conterá um dossiê concluído por tarefa. F2.2-R1 permanece dentro
   de F2.2 porque é recongelamento da mesma unidade de PR; o gate de saída F0 permanece em F0.6.
6. Serão migrados exatamente 19 dossiês: F0.0–F0.6, F1.1–F1.5, F2.1–F2.6 e DOC-F2-STATUS.
7. O payload histórico de cada dossiê será extraído mecanicamente do snapshot fonte por heading,
   sem resumo nem reescrita. Um manifesto JSON registrará commit/hash fonte, ID, path e SHA-256 do payload.
8. Regras permanentes permanecem em `.agents/AGENTS.md` e no plano principal; contexto histórico de
   governança e promoções fica acessível pelo índice, pelos dossiês, pelo manifesto e pelo Git.
9. `AGENTS.md` passará a exigir leitura integral do painel curto, do dossiê ativo apontado e da fase
   ativa no plano. Resultado/aceite/rollback detalhados serão atualizados no dossiê, não duplicados no painel.
10. Os testes documentais passarão a examinar Markdown recursivamente e um teste estrutural impedirá
    regressão para painel monolítico, dossiê ativo ambíguo, IDs duplicados ou payload histórico adulterado.
11. Não será criada fonte de verdade gerada, banco, YAML de estado ou dependência nova.

### Recongelamento R1 — representação canônica do snapshot

O primeiro disparo do migrador encerrou antes de qualquer escrita porque o hash inicial havia sido
calculado sobre o checkout CRLF, enquanto a extração usa o blob Git LF. O escopo, o commit fonte e o
conteúdo não mudam. O critério passa a validar o hash LF `f0f1a187…`; o hash CRLF permanece registrado
como evidência do baseline Windows. Nenhum critério foi removido ou enfraquecido.

### Recongelamento R2 — exemplos históricos e regressão de mojibake

O primeiro aceite focado após a extração concluiu `11 passed` e falhou somente em
`test_source_docs_and_readme_have_no_known_mojibake`: o payload imutável de F0.2 contém os exemplos
literais `AutÃ´nomo`, `âœ”` e `Ãndice`, já presentes no snapshot fonte e protegidos pelo SHA-256 do
manifesto. Corrigi-los adulteraria a evidência; deixar o teste varrer esses payloads tornaria a
migração impossível por uma regra autorreferente.

O escopo passa a incluir somente `tests/unit/test_encoding.py` para excluir da busca semântica de
mojibake os caminhos legados enumerados em `migration-manifest.json`. A leitura UTF-8 estrita continua
cobrindo todos os arquivos, inclusive os 19 dossiês, e documentos correntes ou futuros não recebem
exceção. Nenhum critério foi removido: a separação explicita duas propriedades diferentes — bytes
históricos íntegros e texto corrente sem corrupção.

## Escopo congelado

### Permitido

- `TASK.md` — reduzir ao painel corrente e apontar para o dossiê ativo/índice;
- `.agents/AGENTS.md` — alinhar leitura, atualização e imutabilidade dos dossiês concluídos;
- `docs/tasks/README.md` e `docs/tasks/migration-manifest.json` — índice e integridade da migração;
- `docs/tasks/active/**` e `docs/tasks/completed/**` — dossiê atual e 19 arquivos históricos;
- `tests/unit/test_documentation.py` — ampliar descoberta de Markdown para `docs/**/*.md`;
- `tests/unit/test_encoding.py` — isentar da busca de mojibake somente os payloads legados do manifesto;
- `tests/unit/test_task_ledger.py` — invariantes estruturais e hashes do arquivo de dossiês.

### Proibido

- qualquer arquivo em `src/`, `compiler/`, `.github/`, defaults, schemas, `pyproject.toml` ou `uv.lock`;
- `README.md`, plano principal ou outros documentos fora de `.agents/AGENTS.md`, `TASK.md` e `docs/tasks/**`;
- resumir, corrigir ou reinterpretar contratos/resultados históricos durante a extração;
- iniciar F3.1–F3.8, escolher provider, executar tool, criar worktree real ou alterar produto;
- publicar tag, apagar branch/evidência, force-push, bypass ou desenvolvimento direto em `main`.

## Critérios de aceite congelados

```yaml
acceptance:
  migration_integrity:
    command: >-
      executar o migrador mecânico contra git show d48151b:TASK.md; validar IDs/headings únicos,
      19 payloads e todos os SHA-256 do manifesto
    expected: >-
      todo dossiê histórico mapeado exatamente uma vez; payload entre marcadores byte-idêntico ao
      segmento fonte normalizado em LF; nenhum ID ausente ou duplicado
  control_plane:
    command: >-
      python -m pytest tests/unit/test_task_ledger.py -q
    expected: >-
      TASK.md <= 300 linhas, um único estado corrente, no máximo um dossiê ativo, links/IDs válidos,
      19 dossiês concluídos e hashes do manifesto íntegros
  documentation:
    command: >-
      python -m pytest tests/unit/test_documentation.py tests/unit/test_encoding.py -q
    expected: >-
      todo README/docs/**/*.md em UTF-8, newline/fences válidos, claims honestos e links resolvidos
  regression:
    command: >-
      python -m pytest tests/unit tests/e2e -q
    expected: "suite integral verde, sem skip/xfail novo"
  quality:
    command: >-
      python -m mypy src; python -m ruff check .; python -m compileall -q src compiler tests;
      git diff --check
    expected: "todos exit 0"
  scope:
    command: >-
      git diff --name-only checkpoint/docs-task-ledger-r1-ready;
      git diff --exit-code checkpoint/docs-task-ledger-r1-ready -- src compiler .github README.md
      docs/plano_implementacao_harness_operacional.md pyproject.toml uv.lock
    expected: "somente o allowlist documental/testes congelado; produto, CI, plano e dependências idênticos"
```

## Rollback

### Gatilhos

- algum dossiê, heading, payload ou hash do snapshot fonte ficar ausente, duplicado ou alterado;
- o painel exceder 300 linhas ou continuar contendo histórico detalhado concluído;
- mais de um dossiê ativo, link quebrado ou fonte de verdade concorrente aparecer;
- teste documental deixar de cobrir recursivamente `docs/tasks/**`;
- qualquer arquivo fora do allowlist mudar ou qualquer gate falhar;
- a refatoração exigir código da Fase 3, dependência, workflow ou mudança de protocolo remoto.

### Procedimento

Antes de commit, interromper e inverter somente os hunks desta tarefa com `apply_patch` ou remover
somente arquivos novos explicitamente conferidos. Depois de commit, usar `git revert` nos commits
exclusivos de DOC-TASK-LEDGER. Nunca usar reset, clean, checkout destrutivo ou sobrescrever trabalho
preexistente. Preservar o snapshot fonte em Git e o checkpoint local do gate.

### Verificação pós-rollback

Confirmar branch/HEAD/status; comparar `TASK.md` com
`d48151b752aa373756c46bfee58932fa5abf4bf5`; exigir zero diff nos paths proibidos e repetir os testes
documentais/encoding do baseline.

## Checklist de liberação

```text
[x] problema mensurado e responsabilidade conflitante comprovada
[x] main/origin limpas e CI pós-merge do HEAD comprovada verde
[x] branch documental exclusiva e executor único registrados
[x] snapshot fonte, commit e SHA-256 registrados
[x] arquitetura, 19 unidades históricas e limite do painel congelados
[x] allowlist e fronteira F3 explicitamente congelados
[x] aceite de integridade, estrutura, documentação, regressão, qualidade e escopo definido
[x] rollback não destrutivo e gatilhos objetivos registrados
```
