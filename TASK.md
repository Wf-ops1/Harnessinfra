# TASK.md — AI Engineering Harness · Painel de Execução

> **Protocolo:** Este arquivo é a fonte de recuperação de contexto para qualquer agente ou sessão.
> Atualize após cada tarefa concluída. Nunca marque `completed` sem executar critérios de aceite.

---

## 1. Objetivo Final do Projeto

Transformar o pacote Python `ai-engineering-harness v0.1.0` — atualmente um protótipo com integrações
simuladas — em um motor agentic local-first real: um repositório externo poderá ser inicializado,
analisado, modificado em worktree Git isolado, verificado por gates determinísticos, aprovado, promovido
por cherry-pick e revertido com evidência auditável.
Estratégia: Python-first, fail-closed, incremental, sem mocks em produção.

---

## 2. Fonte de Verdade

**Documento principal:** `docs/plano_implementacao_harness_operacional.md`

Contém todas as tarefas, critérios de aceite, gates e invariantes.
Este TASK.md **não substitui** esse documento — ele aponta para ele.

---

## 3. Invariantes — Nunca Violar

| # | Invariante |
|---|-----------|
| 1 | **Reprodutibilidade:** mesmo grafo + mesmas políticas → mesmo digest de artefato compilado |
| 2 | **Confinamento:** todo path validado e confinado ao worktree antes de qualquer efeito |
| 3 | **Sem shell implícito:** comandos como `argv: list[str]`, sempre `shell=False` |
| 4 | **Sem sucesso vazio:** gate obrigatório não executado → `ERROR`, nunca `PASSED` |
| 5 | **Sem mocks em produção:** adapters reais falham com erro tipado quando indisponíveis |
| 6 | **Sem promoção sintética:** dry-run termina em `DRY_RUN_COMPLETED`, não `COMPLETED` |
| 7 | **Sem alteração silenciosa do checkout original:** promoção só por Git explícito e auditado |
| 8 | **Sem segredo persistido:** todo output passa pelo redactor antes de gravação |
| 9 | **Sem estado só em memória:** estado necessário para retomar deve ser persistido |
| 10 | **Sem versão duplicada:** versão do pacote vem de uma única fonte |
| 11 | **Sem política decorativa:** toda política compilada tem enforcement correspondente |
| 12 | **Sem documentação aspiracional como pronta:** capacidades futuras marcadas como planejadas/experimentais |

---

## 4. Definição Global de Pronto

Uma tarefa só é `completed` quando:

- [ ] Código compila sem erro (`python -m compileall`)
- [ ] Todos os critérios de aceite listados foram executados e passaram
- [ ] Testes correspondentes foram escritos e estão verdes
- [ ] Documentação atualizada na mesma mudança
- [ ] Nenhum mock novo introduzido em código de produção
- [ ] Checklist de handoff respondido (seção 15 do documento principal)

Uma **fase** só avança quando todos os gates de saída estão verdes.

---

## 4.1. Protocolo Obrigatório de Defensabilidade

Este protocolo é um **gate anterior à implementação**. Nenhuma tarefa pode mudar de `pending`
para `in_progress`, e nenhum arquivo de código pode ser alterado em nome dela, até que exista um
dossiê de execução preenchido e marcado como `READY`.

O plano principal define **o que** deve ser construído. Este protocolo define **quando há evidência e
condições suficientes para autorizar a execução**, sem substituir nem reduzir os critérios do plano.

### 4.1.1. Condições obrigatórias antes de `in_progress`

| Condição | Evidência mínima exigida |
|---|---|
| **Problema comprovado** | Comando e saída reproduzível, teste falhando, import/compilação falhando, ou referência exata a arquivo e trecho que demonstre uma lacuna objetiva. Para capacidade ausente, busca e inspeção devem provar que ela não existe ou é simulada. Impressão, hipótese ou intenção do plano não bastam. |
| **Baseline conhecido** | Branch, `HEAD`, `git status --short` e mudanças preexistentes registrados. Alteração alheia à tarefa deve ser preservada e explicitamente excluída do escopo. |
| **Escopo congelado** | Objetivo, arquivos/áreas permitidos, itens fora de escopo, dependências e efeitos esperados registrados antes da primeira edição. |
| **Critérios congelados** | Comandos de verificação, resultado esperado e condição de falha definidos antes da implementação. Critério não pode ser enfraquecido para fazer a tarefa passar. |
| **Rollback executável** | Checkpoint Git existente, gatilhos de abortar/reverter, procedimento não destrutivo e validação pós-rollback registrados. |
| **Responsabilidade explícita** | Executor único, data/hora da liberação e estado do gate registrados. |

### 4.1.2. Dossiê obrigatório por tarefa

Antes da transição para `in_progress`, adicionar à própria tarefa ou ao último checkpoint um bloco com
todos os campos abaixo:

```yaml
defensibility:
  task_id: "F0.x"
  gate: "READY | BLOCKED"
  executor: "nome"
  authorized_at: "YYYY-MM-DDTHH:MM:SS-03:00"
  problem_statement: "fato observável que precisa ser corrigido"
  evidence:
    - command: "comando read-only ou teste de reprodução"
      observed: "exit code e resultado relevante"
      location: "arquivo:linha, quando aplicável"
  baseline:
    branch: "branch atual"
    head: "commit completo ou abreviado inequívoco"
    status: "clean ou lista de mudanças preexistentes preservadas"
    checkpoint: "tag ou commit existente"
  frozen_scope:
    allowed: ["arquivos/áreas autorizados"]
    excluded: ["itens explicitamente fora de escopo"]
  frozen_acceptance:
    - command: "comando exato"
      expected: "exit code e resultado esperado"
  rollback:
    triggers: ["condições objetivas para interromper ou reverter"]
    procedure: "git revert dos commits da tarefa ou restauração não destrutiva explicitamente aprovada"
    verify: "comandos que comprovam retorno ao baseline funcional"
```

### 4.1.3. Regra de congelamento e mudança de escopo

1. O dossiê começa como `BLOCKED` enquanto qualquer campo obrigatório estiver ausente ou sem evidência.
2. Somente com todas as condições satisfeitas o gate muda para `READY`; no mesmo checkpoint, a tarefa
   pode mudar para `in_progress`.
3. Se uma descoberta exigir novo arquivo, novo efeito, dependência não prevista ou mudança de critério,
   interromper a implementação, registrar a descoberta e recongelar escopo, aceite e rollback.
4. Se a ampliação for material, criar um novo checkpoint Git antes de retomar.
5. Nunca remover, ignorar ou tornar mais fraco um critério que falhou. Corrigir a implementação ou
   registrar um bloqueio.
6. Rollback não autoriza `git reset --hard`, descarte amplo ou sobrescrita de trabalho preexistente.
   Preferir commits isolados e `git revert`; qualquer restauração destrutiva exige autorização explícita
   e alvo previamente verificado.

### 4.1.4. Gate de liberação

```text
[ ] Problema comprovado com evidência reproduzível
[ ] Baseline Git e mudanças preexistentes registrados
[ ] Escopo permitido e fora de escopo congelados
[ ] Critérios de aceite exatos e resultados esperados congelados
[ ] Checkpoint Git existente e estratégia de rollback validável
[ ] Executor único e horário de autorização registrados
```

Se qualquer item estiver desmarcado, a tarefa permanece `pending` ou `blocked`. Alteração documental
para preparar o próprio dossiê é permitida; alteração de código da tarefa não é.

## 4.2. Ciclo Git obrigatório por tarefa — DEC-009

**Estado:** `ACTIVE` a partir da F2.1. Esta é a regra persistente para qualquer executor futuro e deve
ser lida junto da seção `Ciclo Git obrigatório por tarefa` do plano principal.

```text
main sincronizada + CI verde
  → branch task/<id>-<descricao-curta>
  → auditoria e gate READY
  → implementação exclusiva da tarefa
  → testes/quality gates/build/smoke/escopo
  → checkpoint e TASK atualizados
  → push + um PR autorizado para main
  → CI required verde + merge commit autorizado
  → comprovar merge e CI pós-merge em main
  → somente então criar a branch da próxima tarefa
```

Regras obrigatórias:

1. `main` é a única linha de integração oficial; deve permanecer protegida, testada e sem
   desenvolvimento direto.
2. Cada tarefa `F2.x` e posterior usa uma branch exclusiva criada da `main` já atualizada. Uma branch
   pode ter commits de gate, implementação e fechamento da mesma tarefa, mas não acumula a tarefa
   seguinte.
3. A tarefa seguinte não começa sobre a branch anterior. Primeiro o PR anterior deve estar mesclado e
   o CI pós-merge da `main` deve estar verde.
4. Um PR corresponde a uma tarefa. Preferir merge commit para preservar os commits e permitir revert
   isolado do merge; squash/rebase só ocorre por decisão explícita registrada.
5. `TASK.md` registra somente fatos remotos observados. PR, CI, merge, SHA ou proteção nunca são
   antecipados como concluídos.
6. Push, PR, merge, exclusão de branch/tag remota e mudança de proteção continuam exigindo autorização
   explícita do usuário; force-push e bypass administrativo são proibidos no fluxo normal.
7. Após merge, a branch remota pode ser removida com autorização. Excluí-la não remove os commits já
   incorporados à `main`.
8. Mudança documental transversal usa branch `docs/<descricao-curta>` e PR próprio. Documentação que
   prepara ou conclui uma tarefa acompanha a branch dessa tarefa.
9. Checkpoints locais auxiliam rollback/retomada, mas não substituem commits, PR, CI ou evidência em
   `TASK.md`.
10. Se `main`, upstream, CI, proteção, PR anterior ou worktree divergirem do checkpoint, parar e alinhar
    o estado antes de editar código.

**Exceção histórica:** F1.1–F1.5 foram concluídas linearmente antes da DEC-009 e estão reunidas em
`phase/f1-compiler-unification`. A F1 será promovida por um único PR. Nenhuma implementação da F2 pode
começar antes de esse PR estar incorporado e o CI pós-merge da `main` estar verde. O commit documental
GOV-GIT-001 que adota a própria regra acompanha a branch da F1 e não cria precedente futuro.

### Registro de adoção da DEC-009

```yaml
defensibility:
  task_id: "GOV-GIT-001"
  gate: "READY"
  executor: "Codex"
  authorized_at: "2026-08-06T19:13:04-03:00"
  problem_statement: >-
    O protocolo defensável estava documentado, mas a unidade de branch/PR/merge entre tarefas não;
    um executor futuro poderia voltar a acumular tarefas ou depender do chat para decidir como integrar.
  evidence:
    - command: >-
        rg -n "branch|pull request|PR|merge|checkpoint|force-push" .agents/AGENTS.md TASK.md
        docs/plano_implementacao_harness_operacional.md docs/handoff_fase_1.md
      observed: >-
        checkpoints, proteção e autorização remota existiam, mas nenhuma regra global exigia branch e
        PR exclusivos por tarefa, merge anterior e CI pós-merge antes da tarefa seguinte
    - command: >-
        git status --porcelain=v2 --branch; git rev-parse HEAD; git rev-parse @{upstream};
        git rev-parse checkpoint/f1.5-complete^{}
      observed: >-
        branch phase/f1-compiler-unification limpa e sincronizada; HEAD/upstream/checkpoint F1.5 em
        15e38516e759c308d1d7a759ff03d0537dbcd867 antes desta mudança documental
  frozen_scope:
    allowed:
      - ".agents/AGENTS.md — regra obrigatória para qualquer executor"
      - "docs/plano_implementacao_harness_operacional.md — contrato principal do ciclo Git"
      - "TASK.md — protocolo de retomada, DEC-009, evidência e próxima ação"
    excluded:
      - "qualquer Python, YAML/schema de produção, dependência, runtime ou teste"
      - "criar branch F2.1, iniciar F2, abrir PR, mergear, alterar main/proteção ou publicar tag"
      - "reescrever branches/commits/checkpoints da F1 ou fazer force-push"
  frozen_acceptance:
    - command: "git diff --check; validação UTF-8/Markdown e busca cruzada das regras"
      expected: "exit 0; plano, AGENTS e TASK descrevem o mesmo ciclo sem conflito"
    - command: "git diff --name-only; git diff --exit-code -- src tests pyproject.toml uv.lock"
      expected: "somente os três documentos permitidos; zero mudança de produto/dependência/teste"
  rollback:
    triggers:
      - "regra permitir desenvolvimento direto em main, tarefa seguinte antes do merge ou bypass de CI"
      - "documentos divergirem sobre branch, PR, autorização, merge ou exceção histórica da F1"
      - "qualquer arquivo fora do escopo documental mudar"
    procedure: >-
      antes do commit, inverter somente os hunks documentais com apply_patch; depois do commit, usar
      git revert do commit exclusivo GOV-GIT-001; nunca resetar ou reescrever a F1
    verify: >-
      git status --short; git diff checkpoint/f1.5-complete -- .agents/AGENTS.md TASK.md
      docs/plano_implementacao_harness_operacional.md; confirmar src/tests/lock byte-idênticos
```

---

## 5. Fase Atual

**→ FASE 1 — Contrato de grafo e compilador único**

**Objetivo:** transformar YAMLs declarativos em artefatos executáveis, validados e determinísticos.

**Status da fase:** `completed` — F1.1–F1.5 concluídas; todos os gates e critérios de saída da
Fase 1 estão verdes. A Fase 2 não foi iniciada.

### Coordenação e ambiente observado

| Campo | Valor atual |
|---|---|
| **Executor ativo** | `Codex` — responsável por implementar, validar, manter checkpoints e criar commits locais |
| **Auditor/revisor** | `Antigravity` — somente-leitura por padrão; só edita quando o usuário solicitar explicitamente ou transferir a execução |
| **Workspace** | `C:\Users\walla\OneDrive\Desktop\ai-engineering-harness` |
| **Git** | `available` — branch `phase/f1-compiler-unification`; `checkpoint/f1.4-complete^{}` em `60c7718bfad7b6241943d815051604c02342b139`; `checkpoint/f1.5-ready` ancora o gate e `checkpoint/f1.5-complete` ancora o fechamento local; branch publicada no GitHub por solicitação do usuário, sem tag remota |
| **python_command** | `& 'C:\Users\walla\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'` — Python `3.12.13` |
| **uv_command** | `& '.\build\f0.6-tools\uv\bin\uv.exe'` — uv `0.11.32` restaurado de forma isolada/ignorada, sem PATH ou instalação global; `lock --check` e `sync --all-extras --locked` verdes |
| **Dependências do projeto** | `.venv` gerida pelo uv 0.11.32 com Python 3.12.13 e `uv.lock`; 229 testes + 6 subtests, mypy em 90 arquivos, Ruff, compileall, lock/sync, build e dois smokes isolados verdes no fechamento da F1.5 |
| **Regra de escrita** | apenas um agente escreve por vez |

---

## 6. Fase 1 — Estado e tarefa atual

### F1.1 — Definir schema tipado do grafo

| Campo | Detalhe |
|-------|---------|
| **Status** | `completed` — gate `READY → COMPLETED`; implementação e critérios congelados aprovados |
| **Objetivo** | Criar os dez modelos Pydantic exigidos pelo plano e validar a topologia do grafo em memória, sem integrar ainda compilador, runtime, policies ou defaults |
| **Arquivos potencialmente alteráveis** | `src/ai_engineering_harness/contracts/graph.py` (novo), `src/ai_engineering_harness/contracts/__init__.py`, `tests/unit/test_graph_contracts.py` (novo), `TASK.md` |
| **Dependências** | Fase 0 concluída; Pydantic v2 e namespaces de versão já disponíveis |

#### Auditoria concreta da F1.1

| Superfície | Comportamento observado | Lacuna frente ao plano | Risco/compatibilidade |
|---|---|---|---|
| `src/ai_engineering_harness/contracts/` | Possui modelos de payloads de nós, eventos e transações; o `__init__.py` raiz não exporta modelos de grafo | Os dez modelos F1.1 estão ausentes | Adição pode ser isolada e sem quebrar imports atuais |
| `src/ai_engineering_harness/compiler/compiler.py` | `GraphCompiler` carrega YAML como `dict`, valida somente se um bloco `loop` contém duas chaves e serializa o grafo bruto | Não valida IDs, entrypoint, arestas, terminais, alcançabilidade, tipos ou valor positivo/condição real de retry | Integrá-lo agora ampliaria a F1.1 para F1.4; explicitamente excluído |
| `compiler/` legado | Implementação separada, import dinâmico de contratos por path, `PolicyValidator` valida somente `graph.name` e emite outro formato de artefato | Duplica compilação e não aplica o contrato F1.1 | Registry seguro pertence à F1.2, policies à F1.3 e unificação à F1.4 |
| `defaults/graphs/*.yaml` | Cinco grafos usam `graph_schema_version=1.0`, mas nenhum declara entrypoint, terminais ou tipo explícito; todas as arestas de término/retry incluem alvos não declarados | Todos falhariam no schema estrito alvo | Não migrar silenciosamente na F1.1; correção fica para a integração/unificação da Fase 1 |
| `versioning.py` | Já separa `GRAPH_SCHEMA_VERSION=1.0` e `ARTIFACT_SCHEMA_VERSION=1.0` | Nenhuma lacuna de versão necessária à F1.1 | Reutilizar constantes sem editar o arquivo |
| CLI/runtime/consumidores | CLI usa somente o compilador oficial; `MAFAdapter` valida apenas `header.runtime_provider`; testes atuais compilam specs mínimos inválidos | Nenhum consumidor usa um `GraphSpec`/`CompiledGraphArtifact` tipado | F1.1 será aditiva; adoção fica para F1.4/F1.5 |

#### Gate de defensabilidade da F1.1

| Campo | Estado atual |
|---|---|
| **Gate** | `READY → COMPLETED` — execução permaneceu no escopo e todos os critérios congelados passaram |
| **Checkpoint de rollback** | `checkpoint/pre-f1.1-defensibility` → `4e3a3531cea44aadcebb9ff3b3e763b4e53adba6` |
| **Checkpoint de liberação** | `checkpoint/f1.1-ready` — tag local no commit documental que contém este dossiê; não publicada |
| **Próximo passo permitido** | Em nova execução, implementar somente os arquivos/símbolos congelados; descoberta fora do escopo reabre o gate |

```yaml
defensibility:
  task_id: "F1.1"
  gate: "READY"
  executor: "Codex"
  authorized_at: "2026-08-04T12:07:01-03:00"
  problem_statement: >-
    O pacote não possui nenhum dos dez modelos tipados exigidos pela F1.1 e o GraphCompiler atual
    aceita e serializa um grafo com ID duplicado, arestas quebradas, sem metadata, entrypoint ou
    terminais, impedindo que o contrato de topologia seja aplicado de forma fail-closed.
  evidence:
    - command: >-
        para cada símbolo F1.1, rg -n -w --glob '*.py' <símbolo>
        src/ai_engineering_harness
      observed: >-
        exit 1 para GraphSpec, GraphMetadata, NodeSpec, AgentNodeSpec,
        DeterministicNodeSpec, HumanApprovalNodeSpec, TerminalStateSpec,
        RetryPolicySpec, ToolPermissionSpec e CompiledGraphArtifact
      location: "src/ai_engineering_harness/contracts/"
    - command: >-
        .venv/Scripts/python.exe -c <probe temporário que chama
        GraphCompiler.compile_graph com dois IDs 'duplicate', arestas para alvos ausentes e sem graph/terminais>
      observed: >-
        exit 0; INVALID_GRAPH_COMPILED=True; artefato gravado no TemporaryDirectory e removido ao final
      location: "src/ai_engineering_harness/compiler/compiler.py:19-65"
    - command: >-
        .venv/Scripts/python.exe -c <auditoria read-only dos cinco defaults, entrypoint,
        terminal_states, type e destinos de on_success/on_failure>
      observed: >-
        exit 0; todos os cinco têm entrypoint=None, zero terminais e type ausente em todos os nós;
        todos possuem alvos não declarados, incluindo END e rotas de retry/escalation/revert
      location: "src/ai_engineering_harness/defaults/graphs/*.yaml"
    - command: >-
        inspeção de src/ai_engineering_harness/compiler/compiler.py, compiler/compile.py,
        compiler/validators/*.py, runtime/maf_adapter.py e consumidores via rg
      observed: >-
        dois formatos/caminhos de compilação; validator oficial apenas de chaves de loop;
        validator legado importa Python por path; runtime confere apenas runtime_provider
      location: "src/ai_engineering_harness/compiler/; compiler/; src/ai_engineering_harness/runtime/maf_adapter.py"
  baseline:
    source_branch: "main"
    branch: "phase/f1-graph-contract"
    head: "4e3a3531cea44aadcebb9ff3b3e763b4e53adba6"
    origin_main: "4e3a3531cea44aadcebb9ff3b3e763b4e53adba6"
    status: "clean antes do dossiê; somente build/dist/caches ignorados produzidos pela revalidação"
    checkpoint: "checkpoint/pre-f1.1-defensibility"
    f0_checkpoint: "checkpoint/f0.6-complete^{} = fd4de2c119daf9a401f450a907f1d07bf3f580e9; ancestral"
    remote_tags: "nenhuma"
    current_ci: >-
      run 30920640518 no HEAD observado, completed/success, 11/11 jobs e CI required=success;
      marco 30917657879 também completed/success, 11/11
    branch_protection: >-
      API pública confirma main protected=true; detalhes strict/enforce_admins/force-push/delete
      permanecem na última evidência autenticada da F0 porque a reconsulta granular retornou 401
      e não havia sessão/credencial autenticada disponível; nenhuma divergência observada
  frozen_decisions:
    model_policy: "Pydantic v2; strict=True, frozen=True e extra='forbid' em todos os modelos"
    public_api: >-
      os dez símbolos exigidos serão definidos em contracts/graph.py e reexportados por contracts/__init__.py
    graph_metadata: >-
      name, graph_schema_version, definition_version, entrypoint, status e description opcional;
      schema_version será aceito somente como alias de entrada do graph_schema_version e a saída
      canônica usará graph_schema_version, preservando DEC-003
    graph_shape: >-
      GraphSpec conterá graph, nodes, terminal_states, policies e contracts; IDs de nós e terminais
      compartilharão namespace único
    node_union: >-
      NodeSpec será união discriminada por type=agent|deterministic|human_approval;
      on_success e on_failure serão obrigatórios para impedir aresta implícita
    agent_node: >-
      exige role, input_contract e output_contract; pode declarar tool_permissions;
      campos de executor determinístico/humano serão proibidos pelo modelo estrito
    deterministic_node: >-
      exige executor determinístico explícito e o campo compatível com a variante
      (policy_ref, gate_name ou command); campos de agente/human approval são inválidos
    human_node: >-
      exige estratégia de aprovação explícita; campos de agente ou executor determinístico são inválidos
    terminal_state: "outcome restrito a success|failure; ao menos um de cada obrigatório"
    retry_policy: >-
      max_iterations será inteiro estritamente positivo e exit_condition string não vazia;
      cada nó participante de ciclo deverá declarar retry_policy
    tool_permission: >-
      referência de tool não vazia e effect restrito a allow|deny; enforcement permanece na F1.3/F5
    topology: >-
      entrypoint deve ser nó existente; toda aresta deve resolver para nó ou terminal;
      todos os nós devem ser alcançáveis a partir do entrypoint
    artifact: >-
      CompiledGraphArtifact tipará apenas metadata de versão e GraphSpec resolvido necessários à F1.1;
      digests, fontes, normalização, atomicidade e integração runtime permanecem F1.5
  frozen_scope:
    allowed:
      - "src/ai_engineering_harness/contracts/graph.py — criar exclusivamente os dez modelos e validações F1.1"
      - "src/ai_engineering_harness/contracts/__init__.py — reexportar exclusivamente a API pública F1.1"
      - "tests/unit/test_graph_contracts.py — testes positivos, negativos, serialização e API pública"
      - "TASK.md — transições, evidências, resultado e checkpoints da F1.1"
      - "build/f1.1-*; build/; dist/; C:/tmp — temporários ignorados/confinados de verificação"
    excluded:
      - "src/ai_engineering_harness/compiler/**, compiler/** e CLI — integração/unificação F1.4"
      - "src/ai_engineering_harness/defaults/graphs/*.yaml — migração dos defaults após adoção do compilador único"
      - "runtime/maf_adapter.py e runtime/engine.py — consumo do artefato tipado F1.4/F1.5/F2"
      - "registry/import de contratos F1.2; policies/roles/tools F1.3; enforcement de permissions F5"
      - "digests, timestamps, escrita atômica e determinismo de compilação F1.5"
      - "pyproject.toml, uv.lock, versioning.py, dependências e ambiente global"
      - "push, PR, merge, tag remota ou alteração de branch protection"
  compatibility_strategy:
    current_consumers: >-
      nenhuma chamada existente será redirecionada na F1.1; os modelos serão API aditiva e só
      dados validados explicitamente por GraphSpec receberão o novo contrato
    defaults: >-
      os cinco YAMLs atuais permanecem inalterados e reconhecidamente incompatíveis; migração será
      feita quando o compilador oficial passar a consumir GraphSpec, sem fallback permissivo
    legacy_compiler: >-
      compiler/ permanece somente como evidência de dívida até F1.2-F1.4; F1.1 não o legitima nem altera
    versions: >-
      graph_schema_version e artifact_schema_version permanecem 1.0; evolução incompatível exige
      tarefa de migração e novo gate, não mudança silenciosa
  frozen_acceptance:
    - command: >-
        <uv_command> run python -m pytest tests/unit/test_graph_contracts.py
        tests/unit/test_public_module_imports.py tests/unit/test_versioning.py -q
      expected: >-
        exit 0; grafo válido e round-trip do artefato passam; os dez símbolos são públicos;
        zero skips
    - command: >-
        casos negativos em test_graph_contracts.py para ID duplicado, entrypoint ausente/desconhecido,
        terminal success/failure ausente, aresta quebrada, nó inalcançável, aresta implícita,
        ciclo sem retry, max_iterations zero, exit_condition vazia, tipo/campos incompatíveis e extra desconhecido
      expected: "cada caso levanta pydantic.ValidationError; nenhum inválido é aceito ou normalizado silenciosamente"
    - command: "<uv_command> run python -m pytest -q"
      expected: "exit 0; 73+ testes, 6 subtests e os novos testes F1.1 passam"
    - command: >-
        <uv_command> run python -m mypy src; <uv_command> run python -m ruff check .;
        <uv_command> run python -m compileall -q src compiler tests; git diff --check
      expected: "todos exit 0; sem redução de regras, ignores ou skips"
    - command: >-
        <uv_command> run python -m build; com uv isolado no PATH do subprocesso,
        <uv_command> run python tests/ci/smoke_wheel.py
      expected: >-
        exit 0; wheel contém contracts/graph.py; import público funciona da instalação externa;
        metadata, __version__ e CLI permanecem 0.1.0
  rollback:
    triggers:
      - "necessidade de alterar compilador, runtime, YAML default, dependency ou arquivo fora do escopo"
      - "modelo precisar executar/importar código fornecido por projeto não confiável"
      - "critério negativo aceitar coerção, extra ou topologia inválida"
      - "qualquer teste F0, build, smoke ou API pública existente regredir"
      - "critério congelado precisar ser removido, ignorado ou enfraquecido"
    procedure: >-
      interromper e preservar logs; antes de commit inverter somente os hunks F1.1 por apply_patch;
      depois de commit usar git revert nos commits exclusivos da F1.1; nunca resetar ou descartar
      trabalho preexistente; preservar checkpoint/pre-f1.1-defensibility
    verify: >-
      git status --short; git diff checkpoint/pre-f1.1-defensibility --
      src/ai_engineering_harness/contracts tests/unit/test_graph_contracts.py TASK.md;
      repetir pytest integral, mypy, Ruff, compileall, build e smoke da wheel
  external_boundary: >-
    nenhum push, PR, merge, tag remota ou mudança de proteção está autorizado nesta tarefa sem
    pedido explícito adicional do usuário
```

#### Checklist de liberação da F1.1

```text
[x] Problema comprovado com evidência reproduzível
[x] Baseline Git e mudanças preexistentes registrados
[x] Escopo permitido e fora de escopo congelados
[x] Decisões de contrato e estratégia de compatibilidade congeladas
[x] Critérios positivos, negativos e regressão integral congelados
[x] Checkpoint Git local e rollback não destrutivo definidos
[x] Executor único e horário de autorização registrados
```

#### Resultado e handoff da F1.1

| Verificação final | Resultado |
|---|---|
| API pública e casos positivos/negativos focados | exit 0; 28 testes passaram |
| Suíte integral | exit 0; 98 testes + 6 subtests passaram |
| `mypy src` | exit 0; sem issues em 87 arquivos |
| `ruff check .`, `compileall` e `git diff --check` | todos exit 0 |
| Build | exit 0; wheel e sdist geradas; `contracts/graph.py` presente na wheel e zero entradas de bytecode |
| Smoke isolado da wheel | exit 0; metadata, pacote e CLI em `0.1.0`; origem fora do checkout; API de grafo `10/10` importável |
| Escopo congelado | somente `contracts/graph.py`, `contracts/__init__.py`, `test_graph_contracts.py` e `TASK.md` alterados |

| Pergunta obrigatória | Resposta |
|---|---|
| **Qual comportamento anterior foi substituído?** | O pacote não possuía contrato tipado de grafo; specs inválidos podiam permanecer como dicionários sem uma validação topológica comum. |
| **Qual é o novo contrato público?** | Dez símbolos reexportados por `ai_engineering_harness.contracts`: `GraphSpec`, `GraphMetadata`, `NodeSpec`, três subtipos de nó, `TerminalStateSpec`, `RetryPolicySpec`, `ToolPermissionSpec` e `CompiledGraphArtifact`; modelos estritos, imutáveis e com extras proibidos. |
| **Quais erros tipados podem ocorrer?** | `pydantic.ValidationError` para tipos/coerções indevidos, extras, IDs duplicados, entrypoint/arestas inválidos, terminais incompletos, nós inalcançáveis, ciclos sem retry e combinações incompatíveis de executor/campo. |
| **Quais side effects são produzidos?** | Nenhum side effect de runtime; somente validação em memória, arquivos versionados do escopo e artefatos ignorados de teste/build. |
| **Onde o estado é persistido?** | Nos modelos Python, testes unitários, neste painel e no histórico/checkpoints Git locais. |
| **Como a operação é retomada após crash?** | Retomar de `checkpoint/f1.1-complete`, confirmar worktree/branch e preparar o dossiê F1.2 antes de qualquer implementação. |
| **Qual política autoriza a ação?** | Dossiê F1.1 com gate `READY`, escopo congelado e checkpoint local `checkpoint/f1.1-ready`. |
| **Como secrets são protegidos?** | A F1.1 não acessa nem persiste secrets e não realizou chamadas externas. |
| **Quais eventos são emitidos?** | Nenhum evento de domínio ou externo; validações falham de forma síncrona antes de qualquer integração. |
| **Quais testes provam sucesso?** | Construção/serialização dos três tipos de nó, grafo válido, ciclo governado, imutabilidade profunda, round-trip do artefato e os dez exports públicos. |
| **Quais testes provam falha segura?** | Casos negativos rejeitam duplicidade, referências quebradas, ausência de terminais, inalcançabilidade, ciclo sem retry, valores vazios/zero, coerção, extras e combinações incompatíveis. |
| **A wheel instalada externamente foi testada?** | Sim; instalação uv isolada importou os dez símbolos a partir do `site-packages`, fora do checkout. |
| **A documentação foi atualizada?** | Sim; este painel registra resultado, limites e retomada. Compiladores, runtime e YAMLs ainda não consomem o schema e permanecem para F1.2–F1.5. |

---

### F1.2 — Criar registry seguro de contratos

| Campo | Detalhe |
|---|---|
| **Status** | `completed` — gate `READY → COMPLETED`; implementação e critérios congelados aprovados |
| **Objetivo** | Substituir resolução arbitrária por path por um catálogo explícito, produzir schema/digest determinísticos e bloquear execução de Python externo salvo confiança e aprovação exatas |
| **Arquivos potencialmente alteráveis** | `contracts/registry.py` (novo), `contracts/graph.py`, `contracts/__init__.py`, adapter legado `compiler/validators/contract_validator.py`, testes focados, `pyproject.toml`, `uv.lock` e `TASK.md` |
| **Dependências** | F1.1 concluída; Pydantic v2 disponível; validação normativa de JSON Schema exigirá dependência direta `jsonschema` v4 registrada no lock |

#### Auditoria concreta da F1.2

| Superfície | Comportamento observado | Lacuna frente ao plano | Risco/compatibilidade |
|---|---|---|---|
| `compiler/validators/contract_validator.py` legado | Divide `path#Classe`, procura o path na raiz, pacote ou `.harness` e chama `spec_from_file_location` + `exec_module` sem receber decisão de confiança | Executa código Python escolhido pelo projeto durante validação | Execução de código de topo antes de qualquer gate; precisa virar adapter fail-closed sem loader por arquivo |
| Prova controlada em `build/f1.2-audit/` | Um arquivo cujo topo levanta `F1.2_AUDIT_TOP_LEVEL_CODE_EXECUTED` foi efetivamente executado pelo validator e encapsulado em `ContractValidationError` | Confirma explorabilidade, não apenas presença de API perigosa | Artefatos da prova estão ignorados por Git; nenhum código versionado foi criado |
| `src/ai_engineering_harness/compiler/compiler.py` | Valida somente bloco `loop`; compilou um YAML com `missing/schema.json` e `missing/module.py#Payload` e escreveu JSON com exit 0 | Contrato inexistente não interrompe o caminho oficial | Integração completa permanece F1.4; F1.2 entregará o resolver seguro consumível pelo compilador |
| Contratos internos | Há modelos Pydantic espalhados em `contracts/nodes`, `events` e `transactions`, sem catálogo único; `ContextSufficiencyReport` existe em dois módulos | Lookup por nome curto é ambíguo | Nome canônico deve ser totalmente qualificado; aliases só podem ser allowlist exata |
| Grafos default | Cinco YAMLs contêm 24 referências e 11 pares `contracts/...py#Classe` distintos | Formato legado mistura identidade e path executável | Preservar somente os 11 aliases internos conhecidos, resolvidos por mapping; não importar seus paths nem editar YAMLs na F1.2 |
| `GraphSpec`/`CompiledGraphArtifact` | Referências são strings; o artefato possui apenas versões e grafo, sem schema/digest resolvido | Aceite F1.2 não é representável | Adicionar visão resolvida compatível, mantendo construção F1.1 existente válida |
| Fronteira de confiança | `TrustBoundaryEvaluator` expõe `allow_python_contracts`, mas considera um arquivo `.harness/trusted_repository` suficiente e nenhum compilador/validator consulta o resultado | Não há aprovação exata vinculada ao módulo | Registry deve receber confiança e allowlist de aprovação explicitamente; integração de trust/policy fica para F5 |
| JSON Schema e testes | `jsonschema` não está em `pyproject.toml`, `uv.lock` nem `.venv`; não há teste de registry, contrato malicioso ou contrato inexistente | Falta validação normativa e prova fail-closed | Adicionar dependência direta v4 e testes focados sem relaxar gates existentes |

#### Gate de defensabilidade da F1.2

| Campo | Estado atual |
|---|---|
| **Gate** | `READY → COMPLETED` — execução permaneceu no escopo, incluindo o recongelamento R1, e todos os critérios passaram |
| **Checkpoint anterior** | `checkpoint/pre-f1.2-defensibility` → `d61d4e36109f685ef237c5256e046cc71654d719` |
| **Checkpoint de liberação** | `checkpoint/f1.2-ready` será criado no commit exclusivamente documental deste dossiê |
| **Próximo passo permitido** | Em nova execução, implementar somente o escopo congelado; descoberta fora dele reabre o gate |

```yaml
defensibility:
  task_id: "F1.2"
  gate: "READY"
  executor: "Codex"
  authorized_at: "2026-08-04T12:56:59-03:00"
  problem_statement: >-
    O projeto não possui catálogo seguro de contratos: o validator legado executa Python escolhido
    por path durante a compilação, enquanto o compilador oficial aceita referências inexistentes;
    nenhum caminho produz schema e digest resolvidos no artefato.
  evidence:
    - command: >-
        rg -n -i "importlib|spec_from_file_location|module_from_spec|exec_module|contract.?registry"
        src compiler tests
      observed: >-
        o único loader de contratos está em compiler/validators/contract_validator.py e chama
        spec_from_file_location, module_from_spec e exec_module; nenhum ContractRegistry existe
      location: "compiler/validators/contract_validator.py:1-56"
    - command: ".venv/Scripts/python.exe build/f1.2-audit/run_legacy_probe.py"
      observed: >-
        exit 0; ContractValidationError contém F1.2_AUDIT_TOP_LEVEL_CODE_EXECUTED, provando que o
        corpo de malicious_contract.py foi executado durante a validação
      location: "build/f1.2-audit/ — prova ignorada por Git"
    - command: >-
        GraphCompiler(Path('build/f1.2-audit')).compile_graph(
        Path('build/f1.2-audit/missing-contract.yaml'), 'missing-contract')
      observed: >-
        exit 0; escreveu .harness/state/compiled/missing-contract.json preservando referências
        missing/schema.json e missing/module.py#Payload sem resolvê-las
      location: "src/ai_engineering_harness/compiler/compiler.py:39-66"
    - command: >-
        rg -o --no-filename "contracts/...py#Classe" defaults/graphs; ordenar e contar
      observed: "24 ocorrências, 11 referências únicas; todas no formato legado path#Classe"
      location: "src/ai_engineering_harness/defaults/graphs/*.yaml"
    - command: >-
        CompiledGraphArtifact.model_fields.keys(); busca de jsonschema em pyproject.toml e uv.lock;
        busca de ContractValidator/contract registry tests em tests/
      observed: >-
        artefato contém somente artifact_schema_version, package_version e graph; jsonschema e
        testes de segurança do registry estão ausentes
  git_baseline:
    branch: "phase/f1-contract-registry"
    head: "d61d4e36109f685ef237c5256e046cc71654d719"
    base_checkpoint: "checkpoint/f1.1-complete"
    rollback_checkpoint: "checkpoint/pre-f1.2-defensibility"
    worktree: "limpa; somente build/, dist/ e provas ignoradas produzidas pelas verificações"
    remote_boundary: "nenhuma branch ou tag F1 publicada"
  baseline_verification:
    - command: "<uv_command> lock --check"
      observed: "exit 0"
    - command: >-
        <uv_command> run python -m pytest -q -p no:cacheprovider
        --basetemp build/f1.2-audit/full-pytest
      observed: "exit 0; 98 testes e 6 subtests passaram"
    - command: "<uv_command> run python -m mypy src"
      observed: "exit 0; sem issues em 87 arquivos"
    - command: >-
        <uv_command> run python -m ruff check .;
        <uv_command> run python -m compileall -q src compiler tests
      observed: "ambos exit 0"
    - command: >-
        <uv_command> run python -m build; adicionar o diretório do uv registrado somente ao PATH
        do processo; <uv_command> run python tests/ci/smoke_wheel.py
      observed: >-
        build exit 0; smoke exit 0 após expor o uv ao subprocesso; metadata, package e CLI 0.1.0,
        import originado de site-packages fora do checkout
  frozen_contract:
    catalog: >-
      ContractRegistry mantém mapping explícito de nomes totalmente qualificados para classes
      Pydantic internas já importadas pelo pacote; lookup nunca deriva import ou path do nome pedido
    canonical_internal_name: >-
      ai_engineering_harness.contracts.<subpacote>.<modulo>.<Classe>; nome curto é proibido porque
      ContextSufficiencyReport possui duas definições atuais
    legacy_aliases: >-
      os 11 path#Classe usados pelos defaults serão aliases exatos para entradas internas conhecidas;
      qualquer outro .py#Classe será rejeitado sem tocar no filesystem
    external_json_schema: >-
      referência explícita jsonschema:<path-relativo>[#<JSON-Pointer>], restrita ao schema root
      configurado, extensão .json, path real contido no root e documento validado por jsonschema v4
    trusted_python: >-
      referência python:<modulo>:<Classe> só pode importar após repository_trusted=true e presença
      da referência exata em approved_python_contracts; faltar qualquer condição falha antes do import
    python_loader: >-
      spec_from_file_location, module_from_spec e exec_module por path são proibidos; módulo aprovado
      usa import normal por nome e o símbolo deve ser subclasse Pydantic BaseModel
    resolved_contract: >-
      ResolvedContractSpec estrito contém canonical_name, requested_reference, source, JSON Schema e
      digest sha256:<hex> calculado sobre JSON UTF-8 canônico com sort_keys e separadores compactos
    artifact: >-
      CompiledGraphArtifact recebe campo aditivo resolved_contracts com default vazio para preservar
      F1.1; o passo resolve_many da F1.2 deve preenchê-lo e falhar antes da criação se houver referência ausente
    compatibility: >-
      validate_compatibility é chamado somente para pares output/input declarados; digest idêntico é
      compatível e schemas object são comparados conservadoramente por campos required e tipos aceitos;
      composição ou prova indeterminada falha com ContractCompatibilityError, nunca assume compatibilidade
    errors:
      - "ContractRegistryError — base tipada"
      - "InvalidContractReferenceError — sintaxe, path ou símbolo inválido"
      - "ContractNotFoundError — referência sem entrada resolvível"
      - "UntrustedPythonContractError — Python sem confiança/aprovação exatas"
      - "InvalidContractSchemaError — JSON inválido, schema inválido, símbolo não Pydantic ou digest inconsistente"
      - "ContractCompatibilityError — incompatibilidade ou impossibilidade de prova segura"
  frozen_scope:
    allowed:
      - "src/ai_engineering_harness/contracts/registry.py — criar catálogo, modelos, erros, resolução, digest e compatibilidade"
      - "src/ai_engineering_harness/contracts/graph.py — adicionar resolved_contracts ao artefato sem quebrar construção F1.1"
      - "src/ai_engineering_harness/contracts/__init__.py — reexportar exclusivamente a API pública F1.2"
      - "compiler/validators/contract_validator.py — remover loader arbitrário e delegar ao registry seguro preservando adapter legado"
      - "tests/unit/test_contract_registry.py — criar testes positivos, negativos, segurança, digest, aliases e compatibilidade"
      - "tests/unit/test_graph_contracts.py — ampliar somente round-trip/compatibilidade aditiva do artefato"
      - "pyproject.toml e uv.lock — adicionar somente jsonschema v4 como dependência direta e relock consistente"
      - "TASK.md — transições, evidências, resultado e checkpoints F1.2"
      - "build/f1.2-*; build/; dist/; C:/tmp — temporários ignorados/confinados de verificação"
    excluded:
      - "src/ai_engineering_harness/compiler/**, compiler/compile.py e CLI — integração e unificação F1.4"
      - "src/ai_engineering_harness/defaults/graphs/*.yaml e contratos payload existentes — migração não necessária graças a aliases exatos"
      - "policies, roles e tools — F1.3; enforcement de permissions — F5"
      - "security/trust.py, approval e config — integração da fronteira de confiança F5"
      - "runtime, persistência, worktree, providers, indexador e knowledge"
      - "normalização integral, escrita atômica e versões do artefato — F1.5"
      - "push, PR, merge, tag remota ou alteração de branch protection"
  compatibility_strategy:
    f1_1_api: >-
      todos os dez exports e construções válidas F1.1 permanecem; resolved_contracts é aditivo e serializável
    default_graphs: >-
      24 ocorrências continuam textualmente intactas; somente os 11 aliases internos exatos resolvem,
      sem transformar paths fornecidos pelo projeto em imports
    legacy_adapter: >-
      ContractValidator e ContractValidationError permanecem importáveis; validate conserva retorno True
      em sucesso e converte erros do registry em ContractValidationError, mas nunca executa arquivo por path
    official_compiler: >-
      não será alterado nem falsamente declarado seguro na F1.2; F1.4 deverá conectar resolve_many ao caminho oficial
    dependency: >-
      jsonschema passa a dependência direta na major v4, registrada em pyproject e uv.lock; nenhum fallback
      permissivo será usado quando indisponível
  frozen_acceptance:
    - command: >-
        <uv_command> run python -m pytest tests/unit/test_contract_registry.py
        tests/unit/test_graph_contracts.py tests/unit/test_public_module_imports.py -q
      expected: >-
        exit 0; catálogo interno, 11 aliases, JSON Schema, Python aprovado, artifact round-trip,
        digest determinístico e compatibilidade conservadora passam
    - command: >-
        testes negativos para referência ausente/malformada, alias arbitrário, escape/symlink de path,
        JSON/schema inválido, duplicidade, símbolo não Pydantic, digest adulterado e incompatibilidade
      expected: "cada caso levanta o erro tipado congelado; nenhum inválido é omitido ou normalizado"
    - command: >-
        teste com arquivo Python malicioso em repositório não confiável e spy no mecanismo de import
      expected: >-
        UntrustedPythonContractError antes de qualquer import; corpo não executa e sentinel não existe,
        inclusive quando a referência aparece na allowlist mas repository_trusted=false
    - command: >-
        rg -n "spec_from_file_location|module_from_spec|exec_module"
        compiler/validators/contract_validator.py src/ai_engineering_harness/contracts
      expected: "exit 1; loader arbitrário por arquivo completamente ausente do escopo F1.2"
    - command: "<uv_command> lock --check; <uv_command> sync --all-extras --locked"
      expected: "ambos exit 0; jsonschema é dependência direta resolvida no lock"
    - command: "<uv_command> run python -m pytest -q"
      expected: "exit 0; 98+ testes, 6 subtests e todos os novos testes F1.2 passam"
    - command: >-
        <uv_command> run python -m mypy src; <uv_command> run python -m ruff check .;
        <uv_command> run python -m compileall -q src compiler tests; git diff --check
      expected: "todos exit 0; sem redução de regras, ignores ou skips"
    - command: >-
        <uv_command> run python -m build; <uv_command> run python tests/ci/smoke_wheel.py;
        smoke isolado importa ContractRegistry, ResolvedContractSpec e erros públicos
      expected: >-
        wheel/sdist limpas; instalação fora do checkout; versões 0.1.0; API F1.1 preservada e API F1.2 importável
  rollback:
    triggers:
      - "qualquer arquivo Python externo executar sem confiança e aprovação exatas"
      - "path absoluto, traversal, symlink escape ou alias não cadastrado resolver"
      - "contrato ausente, schema inválido ou incompatibilidade não falhar fechado"
      - "digest variar para schema semanticamente idêntico após canonicalização"
      - "API F1.1, default conhecido, lock, teste, build ou smoke regredir"
      - "critério congelado precisar ser removido, ignorado ou enfraquecido"
    procedure: >-
      interromper e preservar logs; antes de commit inverter somente hunks F1.2 por apply_patch;
      depois de commit usar git revert nos commits exclusivos da F1.2; nunca resetar nem descartar
      trabalho preexistente; preservar checkpoint/pre-f1.2-defensibility
    verify: >-
      git status --short; git diff checkpoint/pre-f1.2-defensibility --
      src/ai_engineering_harness/contracts compiler/validators/contract_validator.py
      tests/unit/test_contract_registry.py tests/unit/test_graph_contracts.py pyproject.toml uv.lock TASK.md;
      repetir testes focados, busca de loaders, suíte integral, qualidade, build e smoke
  external_boundary: >-
    nenhum push, PR, merge, tag remota ou mudança de proteção está autorizado nesta tarefa sem
    pedido explícito adicional do usuário
```

#### Checklist de liberação da F1.2

```text
[x] Execução arbitrária por path comprovada com prova controlada
[x] Caminho oficial permissivo e ausência de schema/digest comprovados
[x] Baseline Git limpo, branch e checkpoint de rollback registrados
[x] API, identidade, aliases, confiança, digest e compatibilidade congelados
[x] Escopo permitido e fora de escopo congelados por arquivo/capacidade
[x] Critérios positivos, negativos, regressão integral e smoke congelados
[x] Rollback não destrutivo e fronteira externa definidos
[x] Nenhum código, YAML de produção ou schema F1.2 implementado nesta preparação
```

#### Recongelamento F1.2-R1 — stubs de tipagem do JSON Schema

O primeiro `mypy` focado após adicionar `jsonschema` comprovou que a distribuição não expõe stubs
consumíveis pelo gate atual (`import-untyped` em `jsonschema.exceptions` e `jsonschema.validators`).

| Campo | Decisão congelada |
|---|---|
| **Problema comprovado** | `mypy src/ai_engineering_harness/contracts` falhou com dois erros `import-untyped` e recomendou `types-jsonschema` |
| **Escopo adicional permitido** | Adicionar somente `types-jsonschema` em `[project.optional-dependencies].dev` e atualizar `uv.lock`/`TASK.md` |
| **Comportamento preservado** | `jsonschema` continua a única nova dependência de runtime; nenhuma regra mypy, ignore ou configuração será alterada |
| **Critério** | Mypy focado e integral passam sem `ignore_missing_imports`, `type: ignore` ou exclusão de módulo |
| **Rollback** | Reverter as linhas exclusivas de `types-jsonschema` em `pyproject.toml`, `uv.lock` e este registro; preservar o restante da F1.2 |

#### Resultado e handoff da F1.2

| Verificação final | Resultado |
|---|---|
| Casos focados de registry, grafo e imports públicos | exit 0; 63 testes passaram |
| Suíte integral | exit 0; 135 testes + 6 subtests passaram |
| `mypy src` | exit 0; sem issues em 88 arquivos; `types-jsonschema` usado somente no extra dev |
| `ruff check .`, `compileall` e `git diff --check` | todos exit 0 |
| Busca de loaders arbitrários | zero ocorrências de `spec_from_file_location`, `module_from_spec` ou `exec_module` no adapter/contratos |
| Lock e ambiente | `uv lock --check` e `uv sync --all-extras --locked` exit 0; 41 pacotes resolvidos |
| Build e smoke padrão | wheel/sdist geradas; zero bytecode; metadata, pacote e CLI em `0.1.0`, fora do checkout |
| Smoke público adicional | `18/18` símbolos F1.1/F1.2 e `jsonschema 4.26.0` importados da wheel em `site-packages` |
| Escopo congelado | nove arquivos versionados do allowlist; compilador oficial, CLI, defaults, runtime e trust engine intocados |

| Pergunta obrigatória | Resposta |
|---|---|
| **Qual comportamento anterior foi substituído?** | O validator legado executava qualquer `path.py#Classe`, enquanto o caminho oficial aceitava referências inexistentes; agora a resolução disponível é fechada por catálogo e fonte explícita. |
| **Qual é o novo contrato público?** | `ContractRegistry`, `ResolvedContractSpec` e seis erros tipados; 19 nomes internos canônicos, 11 aliases legados exatos, `jsonschema:<path>#<pointer>` confinado e `python:<módulo>:<Classe>` sob dupla autorização. |
| **Quais erros tipados podem ocorrer?** | `InvalidContractReferenceError`, `ContractNotFoundError`, `UntrustedPythonContractError`, `InvalidContractSchemaError` e `ContractCompatibilityError`, todos derivados de `ContractRegistryError`. |
| **Quais side effects são produzidos?** | Registry interno não produz side effect; JSON Schema apenas lê arquivo confinado; Python externo só pode executar após `repository_trusted=true` e aprovação exata. Testes/build usam somente temporários ignorados. |
| **Onde o estado é persistido?** | Catálogo/aliases em código, dependências em `pyproject.toml`/`uv.lock`, schemas/digests em `ResolvedContractSpec`, testes neste repositório e checkpoints Git locais. |
| **Como a operação é retomada após crash?** | Retomar de `checkpoint/f1.2-complete`; confirmar branch/worktree e preparar o dossiê F1.3 antes de implementar políticas ou ferramentas. |
| **Qual política autoriza a ação?** | Dossiê F1.2 `READY`, `checkpoint/f1.2-ready` e recongelamento F1.2-R1 para stubs sem ignores. |
| **Como secrets são protegidos?** | Nenhuma referência, schema, erro ou digest requer secret; a F1.2 não acessa credenciais nem persiste conteúdo secreto. |
| **Quais eventos são emitidos?** | Nenhum evento externo ou de domínio; resolução retorna valor ou erro síncrono antes da futura integração com compilador/runtime. |
| **Quais testes provam sucesso?** | Catálogo 19/aliases 11, JSON Pointer, digest canônico, Python explicitamente aprovado, artifact round-trip, compatibilidade estrutural e adapter legado conhecido. |
| **Quais testes provam falha segura?** | Contrato ausente, alias arbitrário, traversal/symlink, JSON/schema/pointer inválido, digest adulterado, incompatibilidade e Python sem ambas as autorizações falham; o sentinel malicioso nunca é criado. |
| **A wheel instalada externamente foi testada?** | Sim; smoke uv isolado importou `18/18` símbolos, `jsonschema 4.26.0` e confirmou origem fora do checkout. |
| **A documentação foi atualizada?** | Sim; este painel registra implementação, recongelamento, provas e limites. O compilador oficial só consumirá `resolve_many` na F1.4 e a integração do trust engine permanece F5. |

---

### F1.3 — Validar políticas e ferramentas

| Campo | Detalhe |
|---|---|
| **Status** | `completed` — gate `READY → COMPLETED`; implementação e todos os critérios congelados aprovados |
| **Objetivo** | Validar referências de policy, role e tool por catálogos explícitos, calcular a visão efetiva fail-closed e torná-la representável no artefato tipado |
| **Arquivos potencialmente alteráveis** | Contratos/registry de policies, visão aditiva do artefato, adapter legado, catálogos default estritamente necessários, testes focados e `TASK.md` |
| **Dependências** | F1.1 e F1.2 concluídas; Pydantic v2 e PyYAML já disponíveis; nenhuma dependência nova prevista |

#### Auditoria concreta da F1.3

| Superfície | Comportamento observado | Lacuna frente ao plano | Fronteira congelada |
|---|---|---|---|
| `compiler/validators/policy_validator.py` | `validate` verifica somente `graph.name` e retorna `True`; a lista de policies recebida nunca é inspecionada | Role, tool, autorização, referência e schema desconhecidos são aceitos | Virará adapter para o resolver F1.3; unificação do caminho de compilação continua F1.4 |
| Prova controlada `build/f1.3-audit/probe_f1_3.py` | Validator retornou `True` para `missing_role`, `missing_tool`, `policies/missing.yaml` e uma policy com `unknown_key` | Comprova comportamento permissivo executável | Prova e artefatos permanecem ignorados por Git |
| Compilador oficial | `GraphCompiler` gerou JSON com as mesmas referências inexistentes e exit 0 | O caminho oficial não chama validator de policy | Não alterar `src/.../compiler`, CLI ou formato oficial nesta tarefa; integração é F1.4 |
| Roles default | Seis `agent.yaml`; grafos usam seis roles, mas `production_operator` não possui definição e `knowledge_updater` não existe em `tool_policy.roles_permissions` | Não há catálogo internamente consistente | Completar somente essas duas lacunas e validar identidade exata; persona/runtime real não pertence à F1.3 |
| Tools default | Agentes citam 10 IDs e `tool_policy` cita 16; somente `git_tool` e `terminal_tool` aparecem em campos `tool_name` | Não existe registry canônico das capabilities citadas | Criar catálogo declarativo explícito; presença no catálogo não declara adapter operacional |
| Policies default | Oito YAMLs possuem envelope comum de versão, mas payloads heterogêneos e sem modelos; todas as oito refs aparecem nos grafos | Chaves desconhecidas e conflitos não falham | Registrar as oito refs exatas em schemas Pydantic específicos, sem fallback genérico permissivo |
| Referências de grafo | Todos os defaults incluem `tool_policy`; nós determinísticos usam `verification_policy`/`production_health`; nenhuma lista é resolvida hoje | `policy_ref` pode não existir nem pertencer a `graph.policies` | Exigir resolução exata e vínculo explícito à lista do grafo |
| Runtime e governance | Router reconhece `serena_edit`/`terminal_run`; `PolicyEngine` assume `allowed=["*"]` se ausente | IDs e default permissivo não correspondem ao catálogo declarativo | Não criar aliases nem enforcement F1.3; convergência e decisão antes de side effect são F5 |
| `CompiledGraphArtifact` | Possui `resolved_contracts`, mas nenhuma visão resolvida de policy | Aceite F1.3 não é serializável | Adicionar campo opcional com default vazio; preenchimento pelo compilador oficial é F1.4 |

#### Gate de defensabilidade da F1.3

| Campo | Estado atual |
|---|---|
| **Gate** | `READY → COMPLETED` — execução permaneceu no allowlist e todos os critérios passaram |
| **Checkpoint anterior** | `checkpoint/pre-f1.3-defensibility` → `c0aaadd117e9dfe90b3e7fd3c00392ff3ee01c6e` |
| **Checkpoint de liberação** | `checkpoint/f1.3-ready` será criado no commit exclusivamente documental deste dossiê |
| **Próximo passo permitido** | Preparar somente auditoria e gate F1.4; nenhuma unificação de compilador está autorizada sem novo checkpoint READY |

```yaml
defensibility:
  task_id: "F1.3"
  gate: "READY"
  executor: "Codex"
  authorized_at: "2026-08-04T17:24:21-03:00"
  problem_statement: >-
    Policies, roles e tools são hoje texto não resolvido: o validator legado aceita identidades,
    permissões e chaves arbitrárias, o compilador oficial preserva referências inexistentes e os
    defaults não formam catálogos consistentes nem uma visão efetiva serializável.
  evidence:
    - command: >-
        <uv_command> run python build/f1.3-audit/probe_f1_3.py
      observed: >-
        exit 0; legacy_policy_validator_accepted_unknowns=true e
        official_compiler_accepted_unknowns=true; o artefato preservou missing_role e
        policies/missing.yaml
      location: >-
        compiler/validators/policy_validator.py; src/ai_engineering_harness/compiler/compiler.py;
        build/f1.3-audit/ — prova ignorada
    - command: >-
        enumerar defaults/agents/*/agent.yaml, defaults/policies/tool_policy.yaml e roles dos cinco
        defaults/graphs/*.yaml
      observed: >-
        seis agentes e seis roles usados; production_operator é usado sem agent.yaml e
        knowledge_updater possui agent.yaml mas não seção na tool policy
      location: "src/ai_engineering_harness/defaults/agents, policies e graphs"
    - command: >-
        enumerar allowed_tools/forbidden_tools e comparar com campos tool_name em defaults/tools/*.yaml
      observed: >-
        10 IDs em agentes e 16 na policy; os únicos tool_name são git_tool e terminal_tool, sem
        interseção com os 16 IDs de policy
      location: "src/ai_engineering_harness/defaults/agents, tools e policies/tool_policy.yaml"
    - command: >-
        enumerar graph.policies e node.policy_ref nos cinco grafos default
      observed: >-
        oito refs únicas, todas para os oito YAMLs packaged; nenhuma é resolvida pelo validator atual
      location: "src/ai_engineering_harness/defaults/graphs/*.yaml"
    - command: >-
        rg -n 'allowed=|allowed_tools|tool_name ==' src/ai_engineering_harness/governance
        src/ai_engineering_harness/tools src/ai_engineering_harness/runtime
      observed: >-
        runtime dispatcha serena_edit/terminal_run e PolicyEngine usa wildcard quando config falta;
        não há consumidor da policy compilada
      location: >-
        src/ai_engineering_harness/tools/router.py e governance/policy_engine.py
  git_baseline:
    branch: "phase/f1-policy-validation"
    head: "c0aaadd117e9dfe90b3e7fd3c00392ff3ee01c6e"
    base_checkpoint: "checkpoint/f1.2-complete"
    rollback_checkpoint: "checkpoint/pre-f1.3-defensibility"
    worktree: "limpa antes do dossiê; apenas build/f1.3-audit e bytecode ignorados nas provas"
    remote_boundary: "nenhuma branch ou tag F1 publicada"
  baseline_verification:
    - command: "<uv_command> lock --check"
      observed: "exit 0; 41 pacotes resolvidos"
    - command: "<uv_command> run python -m pytest"
      observed: "exit 0; 135 testes passaram"
    - command: "<uv_command> run python -m mypy src"
      observed: "exit 0; sem issues em 88 arquivos"
    - command: >-
        <uv_command> run python -m ruff check .; <uv_command> run python -m compileall -q src compiler tests
      observed: "ambos exit 0"
  frozen_contract:
    references: >-
      As oito referências packaged atuais usam exclusivamente a forma normalizada
      policies/<nome>.yaml e mapping explícito; vazio, whitespace, barra invertida, absoluto,
      traversal, extensão diferente e referência não registrada falham sem fallback de filesystem.
    strict_policy_schemas: >-
      Cada referência packaged é associada a um modelo Pydantic frozen/strict/extra=forbid
      específico para seu envelope e payload conhecido; não existe modelo coringa. Objetos de
      autorização de role/tool são recursivamente estritos e qualquer chave não declarada falha.
    role_identity: >-
      O ID canônico é agent.yaml.name, deve coincidir com o diretório e ser único. O catálogo passa
      a conter exatamente architecture_analyst, code_agent, knowledge_updater, production_operator,
      requirement_analyst, security_agent e test_agent; role é apenas rótulo humano.
    tool_identity: >-
      defaults/tools/tool_registry.yaml será a única lista canônica de capability IDs e conterá os
      16 nomes referidos por tool_policy mais git_tool e terminal_tool. Cada entrada explicita que é
      capability declarada; existência no registry não afirma disponibilidade de adapter/runtime.
    catalog_consistency: >-
      Todo allowed_tools/forbidden_tools de agente ou policy deve existir no ToolRegistry; toda role
      da tool policy deve existir no RoleRegistry; cada agente deve possuir seção de policy; IDs e
      listas devem ser únicos e allowed/forbidden não podem se sobrepor.
    default_repairs: >-
      Adicionar somente a definição declarativa de production_operator e sua prompt packaged,
      adicionar knowledge_updater à tool_policy com os três tools já declarados pelo agente e criar
      o tool_registry; os demais valores/versionamentos default permanecem inalterados.
    graph_policy_rules: >-
      Toda graph.policies deve resolver exatamente e sem duplicata. Todo node.policy_ref deve
      resolver e também aparecer em graph.policies. Grafo com node agent exige tool_policy; role do
      node deve existir antes de qualquer decisão de tool.
    permission_precedence: >-
      A permissão efetiva começa vazia. Node effect=allow só concede tool registrada presente tanto
      no allowed_tools da role quanto no allowed_tools da tool policy e ausente de forbidden_tools;
      effect=deny remove a tool. Deny sempre vence; duplicata ou allow/deny conflitante no mesmo node
      falha, e node não pode ampliar role/policy.
    resolution_api: >-
      PolicyRegistry.resolve_graph recebe GraphSpec e retorna a tupla resolvida; o adapter legado
      aceita somente mapping com nodes em lista e faz normalização mínima de role, policy_ref e
      tool_permissions, sem fingir validação de topologia ou migrar o grafo para o schema F1.1.
    effective_view: >-
      PolicyRegistry.resolve_graph retorna ResolvedPolicySpec frozen em ordem estável, contendo
      referência, policy_id, versões e somente payload efetivo tipado. Para tool policy, serializa
      apenas roles/nodes usados, allowed/denied finais e exigência de aprovação; não inclui YAML cru,
      comentários, paths absolutos, roles inativas ou objetos mutáveis compartilhados.
    artifact: >-
      CompiledGraphArtifact recebe resolved_policies: tuple[ResolvedPolicySpec, ...] com default vazio,
      preservando construções F1.1/F1.2. Digest semântico, sources e escrita atômica permanecem F1.5.
    errors:
      - "PolicyRegistryError — base tipada do domínio"
      - "InvalidPolicyReferenceError — sintaxe, duplicidade ou referência insegura"
      - "PolicyNotFoundError — policy_ref sem entrada registrada"
      - "InvalidPolicySchemaError — YAML/envelope/payload/chave extra inválidos"
      - "RoleNotFoundError — role ausente ou catálogo inconsistente"
      - "ToolNotFoundError — capability citada sem entrada no registry"
      - "UnauthorizedToolError — allow do node excede role/policy ou conflita com deny"
    adapter: >-
      PolicyValidator e PolicyValidationError legados permanecem importáveis; validate retorna True
      somente após delegação completa e converte PolicyRegistryError em PolicyValidationError com
      contexto, sem omitir policy ausente.
    enforcement_boundary: >-
      F1.3 decide e serializa a visão efetiva em design-time, mas não autoriza side effect. Router,
      PolicyEngine, wildcard, trust, aprovação e bloqueio runtime só podem mudar na F5.
  frozen_scope:
    allowed:
      - "src/ai_engineering_harness/contracts/policies.py — modelos estritos, visão efetiva e erros F1.3"
      - "src/ai_engineering_harness/contracts/policy_registry.py — catálogos e resolução fail-closed"
      - "src/ai_engineering_harness/contracts/graph.py — campo aditivo resolved_policies"
      - "src/ai_engineering_harness/contracts/__init__.py — exports públicos F1.3"
      - "compiler/validators/policy_validator.py — adapter legado delegado, sem loader permissivo"
      - "src/ai_engineering_harness/defaults/tools/tool_registry.yaml — catálogo declarativo canônico"
      - "src/ai_engineering_harness/defaults/policies/tool_policy.yaml — somente knowledge_updater"
      - "src/ai_engineering_harness/defaults/agents/production_operator/{agent.yaml,system_prompt.md}"
      - "tests/unit/test_policy_registry.py e test_policy_validator.py — provas focadas"
      - "tests/unit/test_graph_contracts.py, test_public_module_imports.py e test_structure.py — somente regressões aditivas necessárias"
      - "TASK.md — transições, evidências, resultado e checkpoints F1.3"
      - "build/f1.3-*; build/; dist/; C:/tmp — temporários ignorados/confinados de verificação"
    excluded:
      - "src/ai_engineering_harness/compiler/**, compiler/compile.py e CLI — consumo/unificação F1.4"
      - "src/ai_engineering_harness/defaults/graphs/*.yaml — migração para GraphSpec F1.4"
      - "governance, tools/router.py, runtime, permissions, trust, secrets e approval — enforcement F5"
      - "aliases entre serena_edit/terminal_run e IDs declarativos; adapters reais pertencem F3/F5"
      - "policy externa ao catálogo packaged, Python dinâmico ou busca arbitrária por path"
      - "digest/source manifest, normalização integral e escrita atômica do artefato — F1.5"
      - "pyproject.toml, uv.lock ou nova dependência; qualquer necessidade reabre o gate"
      - "push, PR, merge, tag remota ou alteração de branch protection"
  compatibility_strategy:
    graph_and_artifact: >-
      GraphSpec não muda; resolved_policies é aditivo com default vazio, preservando JSON e construção
      dos artefatos existentes até a integração F1.4.
    packaged_references: >-
      Os oito paths, policy_id, policy_schema_version e definition_version atuais são preservados;
      os YAMLs de grafo não são reescritos.
    legacy_adapter: >-
      Assinaturas públicas e erro externo permanecem, mas sucesso permissivo deixa de ser
      compatibilidade válida; inválidos passam a falhar fechado.
    defaults: >-
      As seis definições de agente existentes e suas permissões não mudam. As adições apenas fecham
      production_operator, knowledge_updater e o catálogo inexistente.
    runtime: >-
      Nenhum consumidor atual é alterado ou declarado governado. F1.4 deverá preencher a visão no
      artefato oficial; F5 deverá consumi-la antes de side effects e remover o wildcard permissivo.
  frozen_acceptance:
    - command: >-
        <uv_command> run python -m pytest tests/unit/test_policy_registry.py
        tests/unit/test_policy_validator.py tests/unit/test_graph_contracts.py
        tests/unit/test_public_module_imports.py tests/unit/test_structure.py -q
      expected: >-
        exit 0; oito policies, sete roles e 18 tools resolvem; visão efetiva, adapter e round-trip passam
    - command: >-
        casos negativos parametrizados para policy/role/tool ausentes, ref insegura, duplicidade,
        conflito allow/deny, tool não autorizada e policy_ref fora de graph.policies
      expected: "cada caso levanta o erro tipado congelado antes de produzir ResolvedPolicySpec"
    - command: >-
        adicionar unknown_key ao topo de cada uma das oito policies e aos objetos de autorização
      expected: "InvalidPolicySchemaError em todos os schemas estritos; nenhuma chave é ignorada"
    - command: >-
        validar cada um dos cinco grafos default pelo adapter contra os catálogos packaged, sem invocar o compilador
      expected: >-
        todas as refs/roles resolvem; nenhuma tool fica sem catálogo; permissões efetivas de nodes sem
        tool_permissions permanecem vazias; nenhum warning/fallback
    - command: >-
        teste de precedência com allow válido, deny, forbidden, node conflitante e tentativa de ampliar role
      expected: >-
        allow válido aparece na visão; deny vence; forbidden/conflito/ampliação falham com UnauthorizedToolError
    - command: >-
        serializar e restaurar CompiledGraphArtifact com resolved_contracts e resolved_policies
      expected: >-
        igualdade estrutural, tuplas imutáveis e ausência de YAML cru/path absoluto; construção antiga sem
        resolved_policies continua válida
    - command: >-
        git diff --name-only checkpoint/pre-f1.3-defensibility...HEAD e rg dos compiladores/runtime
      expected: >-
        somente allowlist F1.3 alterado; compilador oficial, compiler/compile.py, CLI, graphs e runtime idênticos
    - command: >-
        <uv_command> lock --check; <uv_command> run python -m pytest; <uv_command> run python -m mypy src;
        <uv_command> run python -m ruff check .; <uv_command> run python -m compileall -q src compiler tests;
        git diff --check
      expected: "todos exit 0; 135+ testes, sem skips/ignores e lock inalterado"
    - command: >-
        <uv_command> run python -m build; <uv_command> run python tests/ci/smoke_wheel.py;
        smoke isolado importa PolicyRegistry, ResolvedPolicySpec e erros públicos
      expected: >-
        wheel/sdist sem bytecode; instalação fora do checkout; versões 0.1.0; APIs F1.1/F1.2 preservadas
  rollback:
    triggers:
      - "policy, role ou tool ausente/extra resolver ou ser omitida sem erro"
      - "chave desconhecida em schema estrito ser aceita"
      - "node ampliar role/policy, deny perder precedência ou effective view divergir"
      - "catálogo declarar adapter/runtime inexistente como operacional"
      - "API F1.1/F1.2, default conhecido, lock, teste, build ou smoke regredir"
      - "compilador oficial, CLI, graph default, runtime ou dependência precisar mudar"
      - "critério congelado precisar ser removido, ignorado ou enfraquecido"
    procedure: >-
      interromper e preservar logs; antes de commit inverter apenas hunks F1.3 por apply_patch;
      depois de commit usar git revert nos commits exclusivos da F1.3; nunca resetar nem descartar
      trabalho preexistente; preservar checkpoint/pre-f1.3-defensibility.
    verify: >-
      git status --short; git diff checkpoint/pre-f1.3-defensibility -- nos caminhos do allowlist;
      confirmar ausência de mudanças nos caminhos excluídos e repetir baseline integral.
  external_boundary: >-
    nenhum push, PR, merge, tag remota ou mudança de proteção está autorizado nesta tarefa sem
    pedido explícito adicional do usuário
```

#### Checklist de liberação da F1.3

```text
[x] Comportamento permissivo reproduzido no validator legado e compilador oficial
[x] Inconsistências exatas de roles, tools, policies e consumidores registradas
[x] Baseline Git limpo, branch e checkpoint de rollback registrados
[x] Schemas, identidade, precedência, visão efetiva e erros congelados
[x] Escopo permitido e fronteiras F1.4/F1.5/F3/F5 congelados
[x] Critérios positivos, negativos, defaults, regressão integral e wheel congelados
[x] Rollback não destrutivo e fronteira externa definidos
[x] Nenhum código, YAML default ou schema F1.3 implementado nesta preparação
```

#### Resultado e handoff da F1.3

| Verificação final | Resultado |
|---|---|
| Casos focados de policy registry, adapter, grafo, imports e estrutura | exit 0; 71 testes passaram |
| Suíte integral | exit 0; 176 testes passaram |
| `mypy src` | exit 0; sem issues em 90 arquivos |
| `ruff check .`, `compileall` e `git diff --check` | todos exit 0 |
| Catálogos packaged | 8 policies estritas, 7 roles e 18 capabilities declaradas; cinco grafos default resolvidos pelo adapter sem warning/fallback |
| Precedência e falha segura | default-deny e deny-wins provados; role/tool/policy ausentes, extra keys, conflito e ampliação falham com erros tipados |
| Lock e ambiente | `uv lock --check` e `uv sync --all-extras --locked` exit 0; 41 pacotes resolvidos; nenhuma dependência alterada |
| Build e smoke padrão | wheel/sdist 0.1.0 geradas sem bytecode; instalação isolada fora do checkout e CLI verdes |
| Smoke público adicional | 9/9 símbolos F1.3, 8 policies, 7 roles e 18 tools importados da wheel em `site-packages` |
| Escopo congelado | somente os 14 arquivos do allowlist; compilador oficial, `compiler/compile.py`, CLI, grafos default, runtime, governance, adapters, dependências e lock intocados |

| Pergunta obrigatória | Resposta |
|---|---|
| **Qual comportamento anterior foi substituído?** | `PolicyValidator` aceitava qualquer role/tool/policy e ignorava todos os documentos; agora delega a resolução estrita e nunca omite policy não carregada. |
| **Qual é o novo contrato público?** | `PolicyRegistry`, `ResolvedPolicySpec`, schemas de role/tool/policy e sete erros tipados; refs packaged exatas, catálogos consistentes e visão efetiva aditiva no artefato. |
| **Qual é a regra de autorização?** | Permissão de node começa vazia; `allow` exige tool registrada e autorizada simultaneamente pela role e tool policy; `deny` vence e node nunca amplia o catálogo. |
| **Quais side effects são produzidos?** | Apenas leitura dos resources packaged e retorno de valores/erros em design-time; nenhuma tool é executada, nenhum runtime é autorizado e nenhuma policy externa é carregada. |
| **Onde o estado é persistido?** | Schemas e registry em código, catálogos em YAML packaged, visão em `resolved_policies` quando construída e checkpoints em Git local. |
| **Como a operação é retomada após crash?** | Retomar de `checkpoint/f1.3-complete`; confirmar branch/worktree e preparar o dossiê F1.4 antes de integrar qualquer compilador. |
| **Qual política autoriza a ação?** | Dossiê F1.3 `READY` e `checkpoint/f1.3-ready`; implementação permaneceu integralmente no allowlist congelado. |
| **Como secrets são protegidos?** | F1.3 não acessa credenciais; visão efetiva contém somente configuração normalizada e não inclui YAML cru, path absoluto ou secret. |
| **Quais eventos são emitidos?** | Nenhum evento externo ou de domínio; resolução é síncrona e fail-closed. |
| **Quais testes provam sucesso?** | Oito policies, sete roles, 18 tools, cinco grafos default, allow válido, default-deny, artifact com contracts+policies, adapter e wheel instalada. |
| **Quais testes provam falha segura?** | Ref insegura/ausente/duplicada, extra key nas oito policies e autorização aninhada, role/tool ausentes, catálogo inconsistente, ampliação e conflito allow/deny. |
| **A wheel instalada externamente foi testada?** | Sim; smoke `-I` importou 9 símbolos e instanciou os catálogos a partir de `site-packages`, fora de `src`. |
| **A documentação foi atualizada?** | Sim; este painel registra implementação, provas e limites. O compilador oficial só preencherá `resolved_policies` na F1.4; enforcement continua F5. |

---

### F1.4 — Unificar os compiladores

| Campo | Detalhe |
|---|---|
| **Status** | `completed` — gate `READY → IN_PROGRESS → COMPLETED`; todos os critérios congelados aprovados |
| **Objetivo** | Fazer o package compiler ser o único caminho de YAML para `CompiledGraphArtifact`, conectar CLI/wrapper aos validators F1.1–F1.3 e eliminar fallback/formatos/destinos duplicados |
| **Arquivos potencialmente alteráveis** | Compiler oficial e exports, CLI compile/run, wrapper/README legado, adapter/visualizer do artefato, cinco grafos default, consumidores de teste e `TASK.md` |
| **Dependências** | F1.1–F1.3 concluídas; Pydantic, PyYAML e registries disponíveis; nenhuma dependência nova prevista |

#### Auditoria concreta da F1.4

| Superfície | Comportamento observado | Lacuna frente ao plano | Fronteira congelada |
|---|---|---|---|
| Package `GraphCompiler` | Lê YAML como `dict`, verifica apenas duas chaves de `loop`, adiciona header com timestamp e grava `header + graph` | Bypassa GraphSpec, ContractRegistry e PolicyRegistry | Torna-se a única implementação e produz `CompiledGraphArtifact`; digest/atomicidade ficam F1.5 |
| `compiler/compile.py` | Reimplementa leitura, três buscas de policy, adapters legados, GateInjector, schema próprio e saída `graphs/compiled/*.maf.json` | Segundo compilador com semântica, path e artefato diferentes | Virará wrapper fino; adapters F1.2/F1.3 permanecem compatíveis, mas não no caminho oficial |
| Prova `build/f1.4-audit/probe_f1_4.py` | Mesma fonte produziu top-level `header,graph` no package e seis chaves diferentes no legado, em dois destinos; igualdade semântica `false` | Critério de compilador único objetivamente falha | Prova confinada/ignorada por Git |
| `harness compile` | Compilou role/tool/policy, aresta e metadata inválidas com exit 0 e mensagem de sucesso | CLI não usa validators F1.1–F1.3 | Deve delegar ao package compiler e converter erros tipados em exit não zero |
| `harness init` versus `run` | `init` cria `.harness/graphs/specs`; `run` procura `graphs/specs` | Spec inicializada é ignorada | `run` deve usar exclusivamente `.harness/graphs/specs/<workflow>.yaml` |
| Fallback de `run` | Workflow ausente cria YAML mínimo em `state/compiled`, compila e conclui com exit 0 | Fabrica sucesso e artefato sem contrato | Remover integralmente; ausência falha antes de execution ID/estado/audit |
| Cinco grafos packaged | Todos sem entrypoint/status/types/terminals; 19 nós sem `type`, refs de contrato apenas por módulo e arestas externas; incident possui role sem contracts | Nenhum passa `GraphSpec` F1.1 | Migrar somente o necessário para o schema congelado, preservando IDs, policies, contratos e intenção |
| Retries packaged | `retry_bug_fix` e `retry_code_generation` são alvos inexistentes | Resolver como ciclos exige retry explícita em todos os nós participantes | Congelar redirects e `RetryPolicySpec` exatos nos dois grafos |
| `GraphVisualizer` | Usa schema `name/agent/action/next` e inventa aresta sequencial quando `next` falta | Incompatível com GraphSpec e viola aresta explícita | Renderizar apenas IDs, on_success/on_failure e terminais já validados |
| `MAFAdapter` | Exige `header.runtime_provider=maf`; não conhece `CompiledGraphArtifact` | Rejeitará o artefato canônico | Migrar somente o loader/validator; execução de nós continua F2 |
| Testes consumidores | Cinco arquivos compilam YAMLs mínimos inválidos; teste CLI prova hoje o fallback como sucesso | Baseline reforça o protótipo permissivo | Migrar fixtures para GraphSpec e inverter o caso workflow ausente |

#### Gate de defensabilidade da F1.4

| Campo | Estado atual |
|---|---|
| **Gate** | `READY → IN_PROGRESS → COMPLETED` — implementação permaneceu no allowlist e todos os critérios passaram |
| **Checkpoint anterior** | `checkpoint/pre-f1.4-defensibility` → `07c8fc362a4bb791d727b0cb43129e8cabb6a26d` |
| **Checkpoint de liberação** | `checkpoint/f1.4-ready` → `24348e929241e7e06b931d62cda062c0f87d9b86`; confirmado antes da primeira edição |
| **Próximo passo permitido** | Preparar somente a auditoria e o gate F1.5; determinismo/digests/atomicidade continuam sem autorização de implementação |

```yaml
defensibility:
  task_id: "F1.4"
  gate: "READY"
  executor: "Codex"
  authorized_at: "2026-08-04T18:43:07-03:00"
  problem_statement: >-
    O package compiler, o wrapper e a CLI não formam um compilador único: aceitam grafos inválidos,
    geram artefatos incompatíveis em destinos distintos, ignoram os registries F1.2/F1.3 e permitem
    que harness run fabrique e execute um workflow ausente.
  evidence:
    - command: "<uv_command> run python build/f1.4-audit/probe_f1_4.py"
      observed: >-
        exit 0 do probe; official_invalid_compiled=true, CLI inválida exit 0/sucesso, run ausente exit 0
        com fallback, e same_source_produced_same_semantics=false
      location: >-
        src/ai_engineering_harness/compiler/compiler.py; compiler/compile.py;
        src/ai_engineering_harness/cli/main.py; build/f1.4-audit/ ignorado
    - command: >-
        comparar chaves e paths dos dois artefatos produzidos pela mesma fonte
      observed: >-
        package: .harness/state/compiled/semantic-divergence.json com header+graph; legado:
        graphs/compiled/semantic-divergence.maf.json com seis chaves top-level diferentes
      location: "build/f1.4-audit/official-shared-project e legacy-shared-project"
    - command: "<uv_command> run python build/f1.4-audit/audit_default_graphs.py"
      observed: >-
        cinco grafos sem entrypoint/status/terminal_states; 19 nós sem type; 15 refs module-only;
        incident.evaluate_rollback sem contracts e nove classes de targets externos
      location: "src/ai_engineering_harness/defaults/graphs/*.yaml"
    - command: >-
        rg -n 'compile_graph|temp_|graphs/specs|state/compiled|maf.json' src compiler tests
      observed: >-
        duas implementações, dois destinos, fallback temporário e cinco arquivos de testes consumidores
        com fixtures mínimas permissivas
      location: "src/ai_engineering_harness, compiler e tests"
  git_baseline:
    branch: "phase/f1-compiler-unification"
    head: "07c8fc362a4bb791d727b0cb43129e8cabb6a26d"
    base_checkpoint: "checkpoint/f1.3-complete"
    rollback_checkpoint: "checkpoint/pre-f1.4-defensibility"
    worktree: "limpa antes do dossiê; somente build/f1.4-audit e bytecode ignorados nas provas"
    remote_boundary: "nenhuma branch ou tag F1 publicada"
  baseline_verification:
    - command: "<uv_command> lock --check"
      observed: "exit 0; 41 pacotes resolvidos"
    - command: "<uv_command> run python -m pytest"
      observed: "exit 0; 176 testes passaram"
    - command: "<uv_command> run python -m mypy src"
      observed: "exit 0; sem issues em 90 arquivos"
    - command: >-
        <uv_command> run python -m ruff check .; <uv_command> run python -m compileall -q src compiler tests
      observed: "ambos exit 0"
  frozen_contract:
    official_owner: >-
      ai_engineering_harness.compiler.GraphCompiler é a única classe com compile_graph e o único
      código que lê YAML, executa validators e serializa artefato. Nenhum segundo pipeline é permitido.
    source_boundary: >-
      compile_graph recebe Path dentro do project_root real, exige arquivo .yaml regular e bloqueia
      absoluto externo, traversal e symlink escape antes da leitura. YAML vazio, não mapping ou inválido falha.
    workflow_identity: >-
      O nome canônico vem de GraphSpec.graph.name e deve casar com slug [A-Za-z0-9][A-Za-z0-9._-]*.
      workflow_name opcional é preservado apenas por compatibilidade e, quando fornecido, deve ser idêntico.
    validation_order:
      - "1. ler YAML seguro e validar GraphSpec F1.1 integralmente"
      - "2. coletar graph.contracts e input/output de agent nodes; ContractRegistry.resolve_many F1.2"
      - "3. carregar overrides declarativos exatos e PolicyRegistry.resolve_graph F1.3"
      - "4. construir CompiledGraphArtifact e só então criar diretório/gravar saída"
    contract_resolution: >-
      ContractRegistry usa .harness/contracts como schema_root, catálogo/aliases internos F1.2 e
      repository_trusted=false sem approvals. Compatibilidade entre arestas não é inferida porque o
      GraphSpec não declara transformação/mapping; adicionar esse contrato exige recongelamento futuro.
    policy_resolution: >-
      Os catálogos packaged F1.3 são base registrada. Overrides são lidos somente dos paths exatos
      .harness/policies/<nome>, .harness/agents/*/agent.yaml e .harness/tools/tool_registry.yaml;
      nenhum lookup em raiz, import Python ou path alternativo é aceito.
    artifact: >-
      A única saída serializa CompiledGraphArtifact com artifact_schema_version, package_version,
      GraphSpec, resolved_contracts e resolved_policies; não contém header legado, graph_metadata,
      compiled_nodes, policies_applied, runtime_provider ou timestamp de compilação.
    output: >-
      Caminho único .harness/state/compiled/<graph.name>.json sob project_root. O diretório só é criado
      depois de todas as validações. Serialização direta permanece nesta tarefa; escrita atômica é F1.5.
    legacy_wrapper: >-
      compiler/compile.py preserva --graph, resolve relativo ao cwd/project_root, chama exclusivamente
      GraphCompiler.compile_graph e reporta o mesmo output. Não carrega YAML/policies, não injeta gates
      e não constrói JSON. GateInjector é removido por ser mutação implícita/orfã.
    cli_compile: >-
      harness compile delega ao mesmo GraphCompiler; --workflow default deixa de fabricar new-feature,
      usa o nome do grafo e só aceita override idêntico. GraphCompilerError vira ClickException/exit não zero.
    cli_run: >-
      Usa artefato existente ou a spec exata .harness/graphs/specs/<workflow>.yaml. Se ambos faltarem,
      falha não zero antes de execution_id, estado, audit ou arquivo temporário. Nunca consulta graphs/specs.
    visualizer: >-
      GraphVisualizer valida GraphSpec e desenha somente on_success/on_failure e terminal_states;
      não usa agent/action/next nem cria sequência implícita.
    artifact_consumer: >-
      MAFAdapter.load_and_validate passa a retornar CompiledGraphArtifact após model_validate_json;
      remove dependência de header.runtime_provider. RuntimeEngine fora desse loader permanece intocado.
    packaged_graph_migration:
      common: >-
        preservar graph.name, versions, description, policies, node IDs e contratos de node; adicionar
        entrypoint igual ao primeiro node, status=stable, types explícitos, contracts como refs completas
        únicas e terminal_states para todos os destinos finais existentes.
      bug_fix: >-
        retry_bug_fix vira aresta para bug_code_fix; bug_code_fix e test_verification recebem
        max_iterations=2/exit_condition=tests_passed; END é success e escalate_to_human failure.
      new_feature: >-
        retry_code_generation vira aresta para code_generation; code_generation, test_generation e
        verification_gates recebem max_iterations=2/exit_condition=all_required_gates_passed; END é
        success e escalate_to_human/revert_and_fail são failure.
      incident: >-
        evaluate_rollback vira deterministic_policy com production_health e sem role; END é success e
        immediate_human_page/escalate_to_human são failure.
      migration: >-
        human_approval_gate vira type=human_approval/approval_strategy=explicit; END é success e
        escalate_to_human/abort_migration/execute_database_rollback são failure.
      refactoring: >-
        tipos explícitos; END é success e escalate_to_human/revert_and_escalate são failure; sem ciclo novo.
    errors:
      - "GraphCompilerError — base tipada pública"
      - "GraphSourceError — path, arquivo, encoding ou YAML inválido"
      - "GraphValidationError — GraphSpec, contrato, policy, role, tool ou workflow incompatível"
      - "GraphWriteError — falha ao criar/gravar o único output depois da validação"
    f1_5_boundary: >-
      Canonicalização semântica, graph/policy digests, source manifest, required capabilities,
      timestamp fora do digest, escrita atômica e compatibilidade exata de versão permanecem F1.5.
    runtime_boundary: >-
      F1.4 entrega e valida o artefato único, mas não faz RuntimeEngine seguir arestas/nós (F2), não
      implementa adapters (F3) e não aplica resolved_policies antes de side effects (F5).
  frozen_scope:
    allowed:
      - "src/ai_engineering_harness/compiler/compiler.py — único pipeline e erros tipados"
      - "src/ai_engineering_harness/compiler/__init__.py — exports públicos F1.4"
      - "src/ai_engineering_harness/compiler/visualizer.py — GraphSpec/arestas explícitas"
      - "src/ai_engineering_harness/cli/main.py — compile/run delegados e sem fallback"
      - "src/ai_engineering_harness/runtime/maf_adapter.py — somente validação do artefato tipado"
      - "compiler/compile.py e compiler/README.md — wrapper fino e documentação real"
      - "compiler/validators/gate_injector.py — remover implementação implícita não usada"
      - "src/ai_engineering_harness/defaults/graphs/*.yaml — migração estrita congelada dos cinco"
      - "tests/unit/test_compiler_unification.py — provas focadas novas"
      - "tests/unit/test_cli_runtime.py, test_phase5.py, test_agent_centric.py e test_phase6.py — migrar consumidores"
      - "tests/e2e/test_full_lifecycle.py — migrar somente fixture/asserções do artefato"
      - "tests/unit/test_structure.py — provar que todos os defaults compilam se necessário"
      - "TASK.md — transições, evidências, resultado e checkpoints F1.4"
      - "build/f1.4-*; build/; dist/; C:/tmp — temporários ignorados/confinados de verificação"
    excluded:
      - "contracts GraphSpec/registries/policies e seus schemas — F1.1–F1.3 permanecem congelados"
      - "outros arquivos runtime além de maf_adapter.py; FSM/ordem real de nós — F2"
      - "providers, tools/adapters, workspace, indexador e knowledge — F3/F4"
      - "governance, permissions, trust, secrets, budget e approval — enforcement F5"
      - "digest, source manifest, capabilities, normalização e escrita atômica — F1.5"
      - "pyproject.toml, uv.lock ou nova dependência; qualquer necessidade reabre o gate"
      - "push, PR, merge, tag remota ou alteração de branch protection"
  compatibility_strategy:
    package_api: >-
      GraphCompiler(project_root) e compile_graph(path, workflow_name opcional) permanecem; sucesso
      continua retornando Path, mas YAML inválido antes tolerado passa a erro tipado deliberado.
    wrapper: >-
      --graph permanece; destino e schema antigos são removidos. Compatibilidade significa delegação
      e artefato idêntico, não preservar o segundo formato inseguro.
    cli: >-
      comandos e opções compile/run permanecem; --workflow explícito igual continua válido. Workflow
      ausente e spec inválida mudam de falso sucesso para exit não zero.
    defaults: >-
      nomes/IDs/descrições/policies/ref contracts são preservados; apenas campos estruturais, terminais,
      retries e dois nodes ambíguos são normalizados conforme migração congelada.
    artifact_consumer: >-
      MAFAdapter mantém nome/método, mas retorna modelo tipado. RuntimeEngine apenas descarta o retorno
      hoje, portanto nenhuma sequência operacional é alterada nesta fase.
  frozen_acceptance:
    - command: >-
        <uv_command> run python -m pytest tests/unit/test_compiler_unification.py
        tests/unit/test_cli_runtime.py tests/unit/test_phase5.py tests/unit/test_agent_centric.py
        tests/unit/test_phase6.py tests/e2e/test_full_lifecycle.py -q
      expected: >-
        exit 0; pipeline único, CLI/wrapper, defaults, paths, adapter e consumidores passam
    - command: >-
        compilar os cinco defaults copiados por harness init e validar cada JSON com CompiledGraphArtifact
      expected: >-
        cinco outputs somente em .harness/state/compiled, com contracts+policies resolvidos, sem warning/fallback
    - command: >-
        casos negativos F1.1–F1.3: metadata/type/edge/terminal/retry inválidos, contract/policy/role/tool ausentes
      expected: >-
        GraphValidationError/exit não zero antes de criar output; diretório compiled permanece ausente ou inalterado
    - command: >-
        harness run definitely-missing em projeto inicializado sem artefato/spec
      expected: >-
        exit não zero; nenhuma spec temp, artifact, execution state ou audit criado; mensagem identifica workflow
    - command: >-
        compilar a mesma spec pelo harness compile e compiler/compile.py --graph em projetos equivalentes
      expected: >-
        JSON semanticamente e byte-a-byte idêntico, mesmo path relativo e mesma API pública
    - command: >-
        casos de source absoluto externo, traversal, symlink escape, extensão não YAML, workflow path-like e nome divergente
      expected: "GraphSourceError ou GraphValidationError; nenhum arquivo fora de project_root é lido/escrito"
    - command: >-
        rg -n 'class GraphCompiler|def compile_graph' src compiler; rg -n 'temp_|graphs/compiled|graphs/specs|GateInjector' src compiler
      expected: >-
        exatamente uma classe/implementação no package; zero fallback, destino legado, lookup errado ou GateInjector
    - command: >-
        testes de GraphVisualizer e MAFAdapter com GraphSpec/CompiledGraphArtifact válidos e adulterados
      expected: "arestas explícitas renderizadas; artefato válido retorna modelo; schema adulterado falha"
    - command: >-
        <uv_command> lock --check; <uv_command> sync --all-extras --locked; <uv_command> run python -m pytest;
        <uv_command> run python -m mypy src; <uv_command> run python -m ruff check .;
        <uv_command> run python -m compileall -q src compiler tests; git diff --check
      expected: "todos exit 0; 176+ testes, sem skips/ignores e dependências/lock inalterados"
    - command: >-
        <uv_command> run python -m build; <uv_command> run python tests/ci/smoke_wheel.py;
        smoke isolado compila spec válida e importa GraphCompiler/errors/CompiledGraphArtifact
      expected: >-
        wheel/sdist limpas; package instalado fora do checkout; API única e defaults packaged funcionais
  rollback:
    triggers:
      - "qualquer YAML inválido produzir output ou exit 0"
      - "wrapper/CLI divergirem em bytes, schema, validators ou destino"
      - "fallback, busca graphs/specs ou segunda implementação permanecer"
      - "default packaged não compilar estritamente sem warning/fallback"
      - "path escapar project_root ou output nascer antes da validação"
      - "mudança exigir relaxar contratos F1.1–F1.3, tocar dependência ou antecipar F1.5/F2/F5"
      - "critério congelado precisar ser removido, ignorado ou enfraquecido"
    procedure: >-
      interromper e preservar logs; antes de commit inverter somente hunks F1.4 por apply_patch;
      depois de commit usar git revert nos commits exclusivos F1.4; nunca resetar nem descartar trabalho
      preexistente; preservar checkpoint/pre-f1.4-defensibility.
    verify: >-
      git status --short; git diff checkpoint/pre-f1.4-defensibility -- nos caminhos do allowlist;
      confirmar contratos/dependências/runtime excluído inalterados e repetir baseline integral.
  external_boundary: >-
    nenhum push, PR, merge, tag remota ou mudança de proteção está autorizado nesta tarefa sem
    pedido explícito adicional do usuário
```

#### Checklist de liberação da F1.4

```text
[x] Bypass F1.1–F1.3, CLI falso sucesso e fallback reproduzidos
[x] Divergência de schema/destino entre os dois compiladores comprovada
[x] Cinco defaults, consumers, visualizer e artifact adapter auditados
[x] Baseline Git limpo, branch e checkpoint de rollback registrados
[x] Pipeline, paths, artefato, erros e migração default congelados
[x] Fronteiras F1.5/F2/F3/F5 e compatibilidade deliberada congeladas
[x] Critérios positivos, negativos, integral e wheel congelados
[x] Nenhum código, YAML default ou teste F1.4 implementado nesta preparação
```

#### Resultado e handoff da F1.4

| Verificação final | Resultado |
|---|---|
| Pipeline e consumidores focados | exit 0; 47 testes passaram, incluindo 25 provas novas de unificação e confinamento |
| Suíte integral confinada | exit 0; 201 testes + 6 subtests passaram |
| `mypy src` | exit 0; sem issues em 90 arquivos |
| `ruff check .`, `compileall` e `git diff --check` | todos exit 0 |
| Compilador único | uma classe e um `compile_graph` no package; wrapper/CLI delegam; `GateInjector`, fallback e destino `.maf.json` removidos |
| Defaults packaged | cinco grafos inicializados e compilados como `CompiledGraphArtifact`, com contratos e policies resolvidos e sem warning/fallback |
| Falha segura | source/path/symlink, GraphSpec, contrato, policy, role, tool, workflow e escrita inválidos falham antes de criar ou alterar output |
| Lock e ambiente | `uv lock --check` e `uv sync --all-extras --locked` exit 0; 41 pacotes resolvidos e 40 verificados; dependências/lock inalterados |
| Build e smoke padrão | wheel/sdist `0.1.0` geradas sem bytecode; metadata, pacote e CLI aprovados fora do checkout |
| Smoke público F1.4 | wheel isolada importou `GraphCompiler`, quatro erros e `CompiledGraphArtifact`; `harness init` + cinco compilações passaram em projeto temporário |
| Escopo congelado | 20 paths versionados do allowlist; contratos F1.1–F1.3, dependências, runtime fora do adapter e superfícies F1.5/F2/F5 intocados |

| Pergunta obrigatória | Resposta |
|---|---|
| **Qual comportamento anterior foi substituído?** | Dois compiladores permissivos geravam schemas e destinos diferentes; CLI aceitava inválidos e `run` fabricava um workflow ausente. Agora existe um pipeline tipado único e fail-closed. |
| **Qual é o novo contrato público?** | `GraphCompiler(project_root).compile_graph(path, workflow_name=None) -> Path` valida source, `GraphSpec`, contratos e policies e grava somente `.harness/state/compiled/<graph.name>.json`; CLI e wrapper delegam à mesma API. |
| **Quais erros tipados podem ocorrer?** | `GraphSourceError`, `GraphValidationError` e `GraphWriteError`, derivados de `GraphCompilerError`; CLI converte esses erros em exit não zero. |
| **Quais side effects são produzidos?** | Leitura confinada do YAML e overrides declarativos; somente após validação integral são criados o diretório canônico e um JSON. Build/testes usam apenas temporários ignorados. |
| **Onde o estado é persistido?** | Artefato tipado em `.harness/state/compiled/`, defaults no pacote, regressões nos testes e evidências/checkpoints neste painel e no Git local. |
| **Como a operação é retomada após crash?** | Retomar de `checkpoint/f1.4-complete`, confirmar worktree/branch e preparar o dossiê F1.5 antes de qualquer mudança de determinismo ou versão do artefato. |
| **Qual política autoriza a ação?** | Dossiê F1.4 `READY`, `checkpoint/f1.4-ready` e DEC-007; nenhuma ampliação material foi necessária. |
| **Como secrets são protegidos?** | A compilação não acessa credenciais; Python externo permanece desabilitado e nenhum YAML cru, path absoluto ou secret é serializado na visão resolvida. |
| **Quais eventos são emitidos?** | A compilação não emite eventos; o fluxo runtime existente permanece fora da execução por arestas, reservada à F2. |
| **Quais testes provam sucesso?** | Artefato tipado, bytes idênticos CLI/wrapper, cinco defaults, overrides exatos, visualizer, MAFAdapter, consumidores, suíte integral e dois smokes externos. |
| **Quais testes provam falha segura?** | Metadata/type/edge/terminal/retry, contrato/policy/role/tool, YAML/path/workflow, symlink de source/output, override estrito, write failure e workflow ausente retornam erro sem falso sucesso. |
| **A wheel instalada externamente foi testada?** | Sim; dois smokes uv isolados importaram exclusivamente de `site-packages`; o adicional compilou os cinco defaults distribuídos. |
| **A documentação foi atualizada?** | Sim; wrapper documentado como compatibilidade delegada e este painel registra contrato, provas, limites e retomada F1.5. |

---

### F1.5 — Artefato determinístico e versionado

| Campo | Detalhe |
|---|---|
| **Status** | `completed` — gate `READY → COMPLETED`; implementação 2.0 e todos os critérios congelados aprovados |
| **Objetivo** | Tornar o `CompiledGraphArtifact` canônico, verificável e atomicamente publicado, com versões exatas, digests semânticos, manifest de fontes e capabilities requeridas, sem antecipar execução ou enforcement |
| **Arquivos potencialmente alteráveis** | Contrato do artefato, compilador oficial, loader do artefato, namespace da versão de schema, testes focados/consumidores diretos, documentação do wrapper e `TASK.md` |
| **Dependências** | F1.1–F1.4 concluídas; SHA-256, JSON, tempfile, flush/fsync e replace atômico disponíveis na stdlib; nenhuma dependência nova prevista |

#### Auditoria concreta da F1.5

| Superfície | Estado comprovado | Lacuna frente ao plano | Fronteira congelada |
|---|---|---|---|
| Determinismo bruto | A mesma fonte compilada duas vezes produz bytes idênticos e não há timestamp no envelope | A estabilidade depende da ordem recebida; dois `GraphSpec` topologicamente equivalentes, com `nodes`/`terminal_states` reordenados, validam mas geram SHA-256 de arquivo distintos | Preservar byte-idêntico para o mesmo conjunto exato de fontes e criar digests semânticos sobre visões normalizadas; não adicionar timestamp volátil |
| Envelope atual | `CompiledGraphArtifact` contém somente `artifact_schema_version`, `package_version`, `graph`, `resolved_contracts` e `resolved_policies` | Faltam `graph_digest`, `policy_digest`, índice explícito de contract digests, `source_manifest` e `required_capabilities` | Evolução incompatível deliberada do artifact schema; GraphSpec e registries existentes permanecem as fontes das visões resolvidas |
| Schema/package versions | Compiler escreve as constantes atuais, mas os campos são apenas strings não vazias; o probe carregou `artifact_schema_version=999.0`, `package_version=999.0.0` e `graph_schema_version=999.0` | Nenhuma comparação exata ocorre antes da execução | Artifact schema passa de `1.0` para `2.0`; package/graph/policy schema devem casar exatamente com as constantes instaladas antes de qualquer transição runtime |
| Graph digest | O grafo tipado completo é serializado em `artifact.graph` | Não há digest nem vínculo que detecte mudança válida porém não autorizada; alterar a role preservando forma foi aceito pelo loader | `graph_digest` será SHA-256 da visão canônica do GraphSpec resolvido |
| Policy digest | `resolved_policies` contém a visão efetiva tipada, sem digest | Alterar `human_approval_required` na visão efetiva foi aceito | `policy_digest` será SHA-256 da sequência canônica completa de policies efetivas |
| Contract digests | Cada `ResolvedContractSpec` já contém digest canônico e `CompiledGraphArtifact` chama `verify_integrity`; adulterar schema sem atualizar digest foi rejeitado | Não há índice explícito, ordenado e cruzado com as referências resolvidas | Preservar o digest F1.2 e adicionar `contract_digests` estritamente igual à visão resolvida, sem recalcular por algoritmo concorrente |
| Source manifest | Compiler lê a spec e catálogos/overrides, mas não persiste identidade ou digest de nenhum arquivo usado | Não há proveniência verificável nem forma de saber quais fontes produziram o artefato | Manifest somente com IDs estáveis relativos/package e SHA-256 dos bytes lidos; nunca path absoluto, mtime, temporary path ou secret |
| Required capabilities | O resolver F1.3 produziu `allowed_tools=[serena_mcp]` no probe, mas o envelope não possui campo de capabilities | Consumidor não pode declarar previamente o conjunto de capabilities necessárias | União ordenada e sem duplicata das capabilities efetivamente permitidas aos nodes; disponibilidade/adapters/enforcement permanecem F3/F5 |
| Grafo resolvido | `graph`, `resolved_contracts` e `resolved_policies` são serializados lado a lado | Não há envelope autoconsistente que vincule grafo, policies, contracts, capabilities e digests | Manter o campo público `graph`; o conjunto desses campos e validadores passa a ser a representação resolvida, sem criar um segundo formato |
| Escrita | `compiler.py` chama `Path.write_text` diretamente no destino final | Probe controlado truncou um artefato válido, levantou `GraphWriteError` e deixou `{"torn":` inválido no destino | Temp exclusivo no mesmo diretório, flush+fsync, `os.replace` e limpeza; falha anterior ao replace preserva integralmente o artefato anterior |
| Consumidores | `harness compile` e wrapper são produtores delegados; `harness run` localiza/compila e passa o path; `RuntimeEngine.run_workflow` chama `MAFAdapter.load_and_validate` como primeira ação e descarta o retorno; testes fazem loads diretos | `MAFAdapter` executa apenas `model_validate_json`; não verifica versões, digests, canonicalidade ou capabilities | Alterar somente o loader; RuntimeEngine, CLI, wrapper e execução por arestas permanecem fora do escopo |

#### Gate de defensabilidade da F1.5

| Campo | Estado atual |
|---|---|
| **Gate** | `READY → COMPLETED` — problema, baseline, contrato, escopo, aceite, compatibilidade, rollback e fronteiras foram preservados e todos os critérios passaram |
| **Checkpoint anterior** | `checkpoint/pre-f1.5-defensibility` → `60c7718bfad7b6241943d815051604c02342b139`, o mesmo commit de `checkpoint/f1.4-complete^{}` |
| **Checkpoint de liberação** | `checkpoint/f1.5-ready` — tag local no commit exclusivamente documental deste dossiê; não publicada |
| **Próximo passo permitido** | Parar ao concluir o checkpoint; F2 exige dossiê e gate próprios em nova retomada antes de qualquer implementação |

```yaml
defensibility:
  task_id: "F1.5"
  gate: "READY"
  executor: "Codex"
  authorized_at: "2026-08-06T17:41:23-03:00"
  problem_statement: >-
    O artefato F1.4 é tipado, mas não é autocontido nem defensável: ordens semanticamente
    equivalentes não possuem identidade normalizada, graph/policy/source/capability metadata está
    ausente, versões incompatíveis e alterações válidas de grafo/policy são aceitas pelo loader e
    uma falha após truncar o destino destrói o último artefato válido.
  evidence:
    - command: >-
        git status --porcelain=v2 --branch; git rev-parse HEAD;
        git rev-parse checkpoint/f1.4-complete^{}; git show --no-patch checkpoint/f1.4-complete
      observed: >-
        branch phase/f1-compiler-unification; status limpo; HEAD e tag peeled iguais a
        60c7718bfad7b6241943d815051604c02342b139; commit feat(compiler): unify F1.4 graph compilation
      location: ".git local; nenhuma alteração de outro executor"
    - command: >-
        probe Python confinado que constrói dois GraphSpec válidos com nodes/terminais em ordem
        inversa e serializa CompiledGraphArtifact pelo caminho atual
      observed: >-
        ambos validam; bytes_equal=false; SHA-256 7a34a99637b692ae10579fc690d78c4f7073f27c2919084fdef0c14247f4eb1f
        versus 18198b04b47108b1573231230dfe04d13c44489b5214dfbc0f1f7412de8329b2
      location: "build/f1.5-audit/model-probe; contratos/graph.py"
    - command: >-
        listar CompiledGraphArtifact.model_fields e carregar cópias com versões 999.x via
        MAFAdapter.load_and_validate
      observed: >-
        somente cinco campos atuais; graph_digest, policy_digest, contract_digests, source_manifest
        e required_capabilities ausentes; artifact/package/graph schema incompatíveis aceitos
      location: >-
        src/ai_engineering_harness/contracts/graph.py:230-248;
        src/ai_engineering_harness/runtime/maf_adapter.py:8-17
    - command: >-
        resolver graph de agente com serena_mcp, dois contratos internos e tool_policy; adulterar
        separadamente schema de contrato, role do graph e human_approval_required da policy
      observed: >-
        dois digests sha256 de contrato presentes e schema adulterado rejeitado; graph/policy
        adulterados aceitos; capability efetiva serena_mcp presente somente dentro da policy
      location: >-
        build/f1.5-audit/integrity-probe; contracts/{registry.py,policy_registry.py,graph.py}
    - command: >-
        compilar artefato válido, monkeypatchar Path.write_text para truncar o destino e levantar
        OSError, então chamar GraphCompiler.compile_graph novamente
      observed: >-
        GraphWriteError levantado; artefato anterior não preservado; destino contém somente
        {"torn": e não é JSON válido; compilação repetida sem falha era byte-idêntica
      location: "src/ai_engineering_harness/compiler/compiler.py:93-102; build/f1.5-audit/atomic-probe"
    - command: >-
        rg de CompiledGraphArtifact, model_validate_json, MAFAdapter, graph/policy/source/capability
        digests e APIs de escrita em src compiler tests
      observed: >-
        único consumidor de produção é MAFAdapter chamado no início de RuntimeEngine.run_workflow;
        zero implementação dos campos F1.5 ou escrita temp+replace no compilador
      location: >-
        src/ai_engineering_harness/{cli/main.py,runtime/{engine.py,maf_adapter.py},compiler/compiler.py}
  git_baseline:
    branch: "phase/f1-compiler-unification"
    head: "60c7718bfad7b6241943d815051604c02342b139"
    f1_4_checkpoint: "checkpoint/f1.4-complete^{} = 60c7718bfad7b6241943d815051604c02342b139"
    rollback_checkpoint: "checkpoint/pre-f1.5-defensibility^{} = 60c7718bfad7b6241943d815051604c02342b139"
    worktree: "limpa antes deste dossiê; somente build/f1.5-audit e caches ignorados nas provas"
    other_executor_changes: "nenhuma"
    remote_boundary: "nenhuma branch ou tag F1 publicada; nenhum estado remoto consultado ou alterado"
  baseline_verification:
    - command: "& '.\\build\\f0.6-tools\\uv\\bin\\uv.exe' lock --check"
      observed: "exit 0; 41 pacotes resolvidos"
    - command: >-
        com LOCALAPPDATA/TEMP/TMP confinados em build/f1.5-audit,
        & '.\\.venv\\Scripts\\python.exe' -m pytest -q -p no:cacheprovider
        --basetemp build/f1.5-audit/confined-pytest
      observed: >-
        exit 0; 201 testes e 6 subtests passaram. A tentativa sem confinamento teve 199 pass e
        somente dois PermissionError em AppData/Local bloqueado pelo sandbox; nenhum teste de produto falhou
    - command: "& '.\\.venv\\Scripts\\python.exe' -m mypy src"
      observed: "exit 0; sem issues em 90 arquivos"
    - command: >-
        & '.\\.venv\\Scripts\\python.exe' -m ruff check .;
        & '.\\.venv\\Scripts\\python.exe' -m compileall -q src compiler tests; git diff --check
      observed: "todos exit 0"
  frozen_contract:
    artifact_schema: >-
      ARTIFACT_SCHEMA_VERSION muda de 1.0 para 2.0 porque os novos campos obrigatórios tornam o
      envelope incompatível; GRAPH_SCHEMA_VERSION e POLICY_SCHEMA_VERSION permanecem 1.0 e
      PACKAGE_VERSION permanece a metadata instalada 0.1.0 nesta tarefa
    required_fields: >-
      CompiledGraphArtifact 2.0 exige artifact_schema_version, package_version, graph_digest,
      policy_digest, contract_digests, source_manifest, required_capabilities, graph,
      resolved_contracts e resolved_policies; extra continua proibido e não há defaults vazios
      para metadata de integridade obrigatória
    digest_format: "sha256:<64 hex minúsculos>, calculado sobre JSON UTF-8 canônico com allow_nan=false"
    canonical_json: >-
      mappings por chave; separadores compactos para digest; sem timestamp; somente coleções
      semanticamente não ordenadas são normalizadas — nodes/terminais por id, graph policies/contracts
      por referência, tool_permissions por tool/effect, contracts por referência/nome e policies por referência
    graph_digest: "SHA-256 do GraphSpec canônico completo, incluindo versões, arestas, retries e permissões"
    policy_digest: >-
      SHA-256 da sequência canônica completa de ResolvedPolicySpec, incluindo envelopes e effective_policy;
      nenhuma policy bruta ou inativa é adicionada ao digest efetivo
    contract_digests: >-
      tupla ordenada de objetos requested_reference, canonical_name e digest; deve corresponder
      exatamente, um-para-um, aos ResolvedContractSpec e reutilizar seus digests F1.2 já verificados
    source_manifest: >-
      tupla ordenada de source_kind, source_id e content_digest para todo arquivo efetivamente lido
      ou validado na compilação: graph YAML, JSON Schema externo, policy/role/tool catalog selecionado
      e prompt override validado; project:// usa path POSIX relativo e package:// usa identidade de resource;
      paths absolutos, traversal, temp paths, mtime, timestamp e conteúdo secreto são proibidos
    source_digest: >-
      SHA-256 dos bytes UTF-8 efetivamente lidos; comentários/formatação podem alterar proveniência,
      mas não graph/policy/contract semantic digests após normalização
    internal_contract_sources: >-
      contratos Pydantic internos não expõem paths Python no manifest; package_version, canonical_name,
      schema resolvido e digest os identificam. Python externo continua desabilitado pelo compilador F1.4
    required_capabilities: >-
      tupla lexicograficamente ordenada e sem duplicata da união de allowed_tools das decisões efetivas
      por node na tool policy; denies e catálogo não usado são excluídos; vazio é válido
    resolved_graph: >-
      o campo público graph permanece o GraphSpec canônico e completo; resolved_contracts,
      resolved_policies, seus digests, manifest e capabilities formam o único artefato resolvido;
      não haverá segundo schema, header ou sidecar
    deterministic_serialization: >-
      mesmos bytes de todas as fontes e mesma package version produzem exatamente os mesmos bytes
      UTF-8 com newline final. Fontes semanticamente equivalentes preservam os digests semânticos,
      embora o content_digest de proveniência possa registrar diferença textual
    timestamp: >-
      nenhum compiled_at/timestamp entra no artefato F1.5; timestamps operacionais pertencem à
      execução/auditoria futura e nunca participarão dos digests semânticos
    atomic_write: >-
      criar temp exclusivo no mesmo output_dir, escrever todos os bytes, flush e os.fsync do arquivo,
      fechar, os.replace para o destino e fsync do diretório quando suportado; limpar temp em falha;
      antes do replace o artefato anterior deve permanecer byte-a-byte intacto
    load_order:
      - "1. ler JSON e validar o schema estrito do envelope"
      - "2. comparar artifact/package/graph/policy schema versions exatamente"
      - "3. verificar canonicalidade e recomputar graph/policy/contract digests e capabilities"
      - "4. resolver IDs project/package, reler as fontes e recomputar cada content_digest; fonte ausente ou divergente falha"
      - "5. retornar CompiledGraphArtifact; só então RuntimeEngine pode continuar"
    compatibility_errors:
      - "ArtifactValidationError — base tipada do loader"
      - "ArtifactCompatibilityError — qualquer namespace de versão incompatível"
      - "ArtifactIntegrityError — JSON/schema/canonicalidade/digest/manifest/capabilities inconsistentes"
      - "FileNotFoundError — preservado para path de artefato ausente"
  frozen_scope:
    allowed:
      - "src/ai_engineering_harness/contracts/graph.py — modelos/validators e normalização do envelope F1.5"
      - "src/ai_engineering_harness/contracts/__init__.py — exports públicos exclusivamente F1.5"
      - "src/ai_engineering_harness/compiler/compiler.py — manifest/capabilities/digests, serialização canônica e escrita atômica"
      - "src/ai_engineering_harness/versioning.py — somente ARTIFACT_SCHEMA_VERSION 1.0 -> 2.0"
      - "src/ai_engineering_harness/runtime/maf_adapter.py — compatibilidade/integridade exatas antes da execução"
      - "compiler/README.md — documentar somente o envelope 2.0 e publicação atômica reais"
      - "tests/unit/test_artifact_determinism.py — novas provas positivas/negativas F1.5"
      - "tests/unit/test_graph_contracts.py, test_contract_registry.py e test_policy_registry.py — migrar construções diretas para o envelope 2.0"
      - "tests/unit/test_compiler_unification.py, test_public_module_imports.py e test_versioning.py — regressões de integração/API/versão"
      - "tests/ci/smoke_compiled_artifact.py — smoke isolado novo da wheel e rejeição de artefato adulterado"
      - "TASK.md — transições, evidências, resultado e checkpoints F1.5"
      - "build/f1.5-*; build/; dist/; C:/tmp — temporários ignorados/confinados de verificação"
    excluded:
      - "src/ai_engineering_harness/defaults/**/*.yaml e qualquer YAML/schema de produção"
      - "contracts/registry.py e policy_registry.py — algoritmos/digests F1.2/F1.3 permanecem congelados"
      - "src/ai_engineering_harness/cli/main.py, compiler/compile.py e GraphVisualizer — delegação F1.4 permanece"
      - "src/ai_engineering_harness/runtime/engine.py, FSM, persistência e execução de arestas/nós — F2"
      - "providers, tools/adapters, MCPs, worktree, indexador e knowledge — F3/F4"
      - "governance, PolicyEngine, trust, secrets, budget e approval — enforcement F5"
      - "pyproject.toml, uv.lock, package version, dependências ou runtime Python"
      - "timestamp de execução, auditoria, doctor, recovery, promoção ou rollback operacional — F2/F6/F7"
      - "push, PR, merge, tag remota ou alteração de branch protection"
  compatibility_strategy:
    artifact_1_0: >-
      incompatibilidade deliberada e fail-closed: artefato 1.0 ou sem metadata F1.5 é rejeitado;
      não há preenchimento de digest, upgrade automático, fallback ou migração silenciosa
    package_and_schemas: >-
      package_version deve ser exatamente PACKAGE_VERSION instalada; graph_schema_version exatamente 1.0;
      todo resolved_policy policy_schema_version exatamente 1.0; qualquer diferença exige recompilação
    compiler_api: >-
      GraphCompiler(project_root).compile_graph(path, workflow_name=None) -> Path, CLI/wrapper e
      .harness/state/compiled/<workflow>.json permanecem inalterados
    public_models: >-
      GraphSpec, ResolvedContractSpec e ResolvedPolicySpec preservam campos e comportamento;
      somente a construção direta de CompiledGraphArtifact passa a exigir metadata 2.0 completa
    loader: >-
      MAFAdapter.load_and_validate mantém nome, argumento e retorno, mas passa a falhar tipadamente
      para incompatibilidade ou adulteração antes de o RuntimeEngine produzir side effect
    source_paths: >-
      manifest é portátil entre clones porque não contém root absoluto; package resources usam ID estável
    no_migration: "recompilar a spec é a única migração autorizada de 1.0 para 2.0 nesta fase"
  phase_boundaries:
    f2: >-
      F1.5 valida e retorna o artefato; não segue entrypoint/arestas, não executa node, não persiste
      transição/checkpoint e não implementa resume/crash recovery
    f3: >-
      required_capabilities é declaração compilada; não verifica disponibilidade, não conecta provider,
      Serena/Codebase-Memory/MCP, não executa tool e não cria worktree
    f5: >-
      policy_digest e visão efetiva provam integridade, não autorização runtime; PolicyEngine, deny/approval,
      trust, secrets e budget continuam obrigatórios antes de side effects na F5
  frozen_acceptance:
    - command: >-
        & '.\\build\\f0.6-tools\\uv\\bin\\uv.exe' run python -m pytest
        tests/unit/test_artifact_determinism.py tests/unit/test_graph_contracts.py
        tests/unit/test_contract_registry.py tests/unit/test_policy_registry.py
        tests/unit/test_compiler_unification.py tests/unit/test_public_module_imports.py
        tests/unit/test_versioning.py -q
      expected: >-
        exit 0; envelope 2.0 completo, APIs anteriores, defaults/consumidores, canonicalidade,
        versions, digests, manifest, capabilities e round-trip passam
    - command: >-
        compilar duas vezes o mesmo conjunto de fontes e também specs semanticamente equivalentes
        com ordens diferentes de nodes, terminais, refs e tool_permissions
      expected: >-
        fontes idênticas produzem bytes e todos os digests idênticos; reordenação preserva
        graph/policy/contract digests e somente proveniência textual legitimamente diferente pode divergir
    - command: >-
        adulterar separadamente graph, resolved_policy, contract schema/digest, contract_digests,
        source manifest e required_capabilities no JSON
      expected: >-
        ArtifactIntegrityError em todos os casos antes do retorno; nenhuma alteração válida porém
        não vinculada é aceita e nenhum digest é confiado sem recomputação
    - command: >-
        carregar artifact_schema_version 1.0/999.0, package_version divergente,
        graph_schema_version divergente e policy_schema_version divergente
      expected: >-
        ArtifactCompatibilityError para cada caso antes da primeira transição/arquivo de execução;
        artefato atual 2.0 carrega exatamente uma vez
    - command: >-
        manifest com absolute path, traversal, backslash, ID duplicado, digest inválido, source ausente
        ou package/project ID não canônico
      expected: "ArtifactIntegrityError ou GraphValidationError; nenhum path local absoluto é serializado"
    - command: >-
        graph com allow/deny e duas roles, policy efetiva e catálogo com capabilities não usadas
      expected: >-
        required_capabilities contém somente união sorted/unique dos allowed_tools efetivos;
        deny e capability apenas declarada não aparecem; campo não afirma adapter disponível
    - command: >-
        injetar falha em create/write/flush/fsync/replace do temp com artefato anterior existente
      expected: >-
        GraphWriteError; antes do replace o artefato anterior permanece byte-idêntico e nenhum temp órfão;
        em sucesso o destino contém somente JSON 2.0 integral e validável
    - command: >-
        rg -n 'compiled_at|timestamp' no JSON compilado e compilar os cinco defaults copiados por harness init
      expected: >-
        zero timestamp volátil no envelope; cinco artefatos 2.0 completos, sem warning/fallback,
        todos aceitos pelo loader exato
    - command: >-
        git diff --name-only checkpoint/pre-f1.5-defensibility...HEAD;
        git diff --exit-code checkpoint/pre-f1.5-defensibility -- pyproject.toml uv.lock
        src/ai_engineering_harness/runtime/engine.py src/ai_engineering_harness/cli/main.py
        compiler/compile.py src/ai_engineering_harness/defaults
      expected: "somente allowlist F1.5 alterado; dependências, YAML, CLI/wrapper e runtime engine idênticos"
    - command: >-
        & '.\\build\\f0.6-tools\\uv\\bin\\uv.exe' lock --check;
        & '.\\build\\f0.6-tools\\uv\\bin\\uv.exe' sync --all-extras --locked;
        com LOCALAPPDATA/TEMP/TMP confinados, & '.\\.venv\\Scripts\\python.exe' -m pytest;
        & '.\\.venv\\Scripts\\python.exe' -m mypy src;
        & '.\\.venv\\Scripts\\python.exe' -m ruff check .;
        & '.\\.venv\\Scripts\\python.exe' -m compileall -q src compiler tests; git diff --check
      expected: "todos exit 0; 201+ testes e 6 subtests, sem skips/ignores e lock inalterado"
    - command: >-
        & '.\\build\\f0.6-tools\\uv\\bin\\uv.exe' run python -m build;
        & '.\\build\\f0.6-tools\\uv\\bin\\uv.exe' run python tests/ci/smoke_wheel.py;
        & '.\\build\\f0.6-tools\\uv\\bin\\uv.exe' run python tests/ci/smoke_compiled_artifact.py
      expected: >-
        wheel/sdist sem bytecode; instalação isolada fora do checkout; versões públicas coerentes;
        compile/load 2.0 verde e artefatos incompatível/adulterado rejeitados
  rollback:
    triggers:
      - "mesmas fontes produzirem bytes ou digests diferentes"
      - "graph, policy, contract, manifest ou capabilities adulterados carregarem"
      - "versão incompatível alcançar RuntimeEngine além do loader"
      - "falha anterior ao replace truncar/substituir o último artefato válido ou deixar temp órfão"
      - "manifest expor path absoluto, timestamp, temp path, secret ou omitir fonte efetivamente usada"
      - "capability negada/não usada aparecer como requerida ou required ser confundida com disponível"
      - "implementação exigir YAML, registry F1.2/F1.3, dependência, CLI/wrapper, RuntimeEngine ou fronteira F2/F3/F5"
      - "artifact 1.0 ser aceito por fallback/migração ou critério congelado precisar ser enfraquecido"
    procedure: >-
      interromper e preservar logs/artefatos; antes de commit inverter somente hunks F1.5 por
      apply_patch; depois de commit usar git revert nos commits exclusivos F1.5; nunca resetar,
      descartar ou sobrescrever trabalho preexistente; preservar checkpoint/pre-f1.5-defensibility
    verify: >-
      git status --short; git diff checkpoint/pre-f1.5-defensibility -- nos paths do allowlist;
      confirmar paths excluídos byte-idênticos; repetir baseline F1.4 confinado, lock, mypy, Ruff,
      compileall e os testes F1.5 de versão/integridade/atomicidade
  external_boundary: >-
    nenhum push, PR, merge, tag remota ou mudança de proteção está autorizado nesta tarefa sem
    pedido explícito adicional do usuário
```

#### Checklist de liberação da F1.5

```text
[x] Baseline Git limpo, F1.4 e checkpoint de rollback comprovados
[x] Determinismo atual e divergência por ordem reproduzidos separadamente
[x] Envelope, graph/policy/contract digests, manifest, capabilities e grafo resolvido auditados
[x] Aceitação de versões e adulteração graph/policy reproduzida; integridade de contrato confirmada
[x] Corrupção por escrita interrompida reproduzida sem tocar arquivo rastreado
[x] Consumidores atuais e ordem do loader mapeados
[x] Contrato 2.0, compatibilidade exata e erro tipado congelados
[x] Escopo permitido/proibido e fronteiras F2/F3/F5 congelados
[x] Critérios positivos, negativos, regressão integral, wheel e rollback congelados
[x] Nenhum Python, YAML/schema de produção, teste de implementação, dependência ou runtime alterado
```

#### Resultado e handoff da F1.5

| Verificação final | Resultado |
|---|---|
| Aceitação focada | exit 0; 151 testes passaram para envelope/API, determinismo, versões, digests, manifest, capabilities, escrita atômica e consumers |
| Suíte integral confinada | exit 0; 229 testes + 6 subtests passaram, sem skips ou ignores |
| `mypy src` | exit 0; sem issues em 90 arquivos |
| `ruff check .`, `compileall` e `git diff --check` | todos exit 0 |
| Determinismo e normalização | fontes idênticas geram bytes idênticos; reordenação semântica preserva graph/policy/contract digests; somente o digest textual de proveniência pode mudar |
| Envelope 2.0 | dez campos obrigatórios, sem defaults de integridade, timestamp ou path absoluto; graph/policy/contract digests e capabilities são recomputados |
| Manifest de fontes | graph, JSON Schema externo e catálogos/prompt efetivamente selecionados usam IDs `project://`/`package://` e SHA-256 dos bytes UTF-8 |
| Escrita atômica | temp exclusivo no mesmo diretório, write/flush/fsync/close/replace e fsync de diretório quando suportado; falhas em create/write/flush/fsync/replace preservam bytes anteriores e removem temp |
| Loader fail-closed | versões artifact/package/graph/policy exatas, JSON canônico, envelope, digests, capabilities e todas as fontes verificados antes da primeira transição runtime |
| Cinco defaults | `harness init` compilou bug-fix, incident, migration, new-feature e refactoring; todos foram aceitos pelo loader exato 2.0 |
| Lock e ambiente | `uv lock --check` e `uv sync --all-extras --locked` exit 0; 41 pacotes resolvidos e 40 verificados; `pyproject.toml`/`uv.lock` inalterados |
| Build e smokes | wheel/sdist 0.1.0 geradas; smoke padrão e smoke F1.5 instalaram fora do checkout, compilaram/carregaram 2.0 e rejeitaram versão/adulteração |
| Escopo congelado | somente 13 paths de implementação/teste/documentação do allowlist e `TASK.md`; YAMLs, registries F1.2/F1.3, CLI/wrapper, RuntimeEngine, dependências e fronteiras F2/F3/F5 byte-idênticos |

| Pergunta obrigatória | Resposta |
|---|---|
| **Qual comportamento anterior foi substituído?** | O envelope 1.0 aditivo, gravado diretamente e aceito por mera validação Pydantic, foi substituído por um artefato 2.0 canônico, vinculado por digests/proveniência e publicado atomicamente. |
| **Qual é o novo contrato público?** | `CompiledGraphArtifact` exige as dez visões congeladas; `GraphCompiler.compile_graph(...) -> Path` preserva API/destino; `MAFAdapter.load_and_validate(path) -> CompiledGraphArtifact` só retorna após compatibilidade e integridade completas. |
| **Quais erros tipados podem ocorrer?** | O compilador preserva `GraphSourceError`, `GraphValidationError` e `GraphWriteError`; o loader preserva `FileNotFoundError` e adiciona `ArtifactValidationError`, `ArtifactCompatibilityError` e `ArtifactIntegrityError`. |
| **Quais side effects são produzidos?** | Leitura confinada das fontes selecionadas e publicação atômica de um único JSON em `.harness/state/compiled/`; nenhum node, tool, provider, policy runtime ou evento é executado. |
| **Onde o estado é persistido?** | No artefato 2.0 canônico, incluindo grafo/contratos/policies resolvidos, digests, manifest e capabilities; evidências e checkpoint ficam no Git/TASK. |
| **Como a operação é retomada após crash?** | Artefato anterior permanece íntegro antes do replace; retomar de `checkpoint/f1.5-complete`, verificar branch/status e abrir novo dossiê antes de F2. |
| **Qual política autoriza a ação?** | Dossiê F1.5 `READY`, `checkpoint/f1.5-ready`, contrato congelado e DEC-008; nenhuma ampliação material ocorreu. |
| **Como secrets são protegidos?** | O manifest contém somente IDs relativos/package e digests, nunca conteúdo, path absoluto, mtime, temp path ou credencial; Python externo permanece desabilitado. |
| **Quais eventos são emitidos?** | Nenhum; timestamps e eventos operacionais pertencem às fases runtime/observabilidade futuras. |
| **Quais testes provam sucesso?** | Bytes repetidos, reordenação semântica, cinco defaults, round-trip tipado, capabilities efetivas, loader exato, suíte integral e dois smokes externos da wheel. |
| **Quais testes provam falha segura?** | Adulterações separadas de graph/policy/contracts/index/manifest/capabilities, versões divergentes, IDs inseguros/ausentes/duplicados, JSON não canônico e cinco pontos de falha atômica. |
| **A wheel instalada externamente foi testada?** | Sim; os dois smokes uv isolados importaram de `site-packages`; o smoke F1.5 compilou/carregou 2.0 e rejeitou adulteração e package version divergente. |
| **A documentação foi atualizada?** | Sim; `compiler/README.md` descreve apenas envelope 2.0, publicação atômica e limites reais, e este painel fecha a Fase 1. |

**Estado de parada obrigatório:** a F1.5 e a Fase 1 estão `completed`. A implementação da Fase 2
não foi iniciada; qualquer continuação exige novo dossiê de defensabilidade.

---

## 6.1. Histórico detalhado da Fase 0

---

### F0.0 — Preflight do workspace e coordenação dos agentes

| Campo | Detalhe |
|-------|---------|
| **Status** | `completed` |
| **Objetivo** | Definir um executor único e comprovar Python/Git disponíveis antes de qualquer alteração de código |
| **Arquivos envolvidos** | `TASK.md`, `.agents/AGENTS.md`; nenhuma alteração de código nesta tarefa |
| **Implementação esperada** | (1) escolher um único executor; (2) detectar `uv`, `python` e `py`; (3) registrar `python_command` com versão `>=3.11`; (4) verificar Git somente se `.git` existir; (5) se `.git` estiver ausente, solicitar decisão para restaurar histórico ou criar baseline; (6) não executar `git init` nem instalar runtime sem autorização |
| **Critérios de aceite** | executor identificado; `python_command` válido ou bloqueio registrado; estado Git registrado; checkpoint e próxima ação atualizados |
| **Comandos de verificação** | PowerShell: `Get-Command uv, python, py, git -ErrorAction SilentlyContinue`; filesystem: `Test-Path -LiteralPath .git`; executar `git rev-parse --is-inside-work-tree` apenas se o teste anterior retornar `True` |
| **Dependências** | nenhuma |

> F0.0 validada: executor Codex definido; Git disponível; Python 3.12.13 detectado. Se o executor ou ambiente mudar, reabrir F0.0 e repetir o preflight.

---

### F0.1 — Corrigir erros bloqueantes de código

| Campo | Detalhe |
|-------|---------|
| **Status** | `completed` — critérios congelados executados e aprovados |
| **Objetivo** | Eliminar erros de sintaxe, imports quebrados e assinaturas inválidas que impedem importação do pacote |
| **Arquivos envolvidos** | `src/ai_engineering_harness/migrations/runner.py`, todos os módulos públicos do pacote |
| **Implementação esperada** | (1) Corrigir assinatura inválida em `migrations/runner.py`; (2) executar `compileall` em `src/`, `compiler/`, `tests/`; (3) corrigir imports quebrados; (4) adicionar teste que importe todos os módulos públicos |
| **Critérios de aceite** | comando Python registrado executa `-m compileall -q src compiler tests` com exit 0; import de `ai_engineering_harness.migrations` com exit 0 |
| **Comandos de verificação** | `& 'C:\Users\walla\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m compileall -q src compiler tests`; depois `& 'C:\Users\walla\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -c "import ai_engineering_harness.migrations"` |
| **Dependências** | F0.0 concluída |

#### Gate de defensabilidade da F0.1

| Campo | Estado atual |
|---|---|
| **Gate** | `READY → COMPLETED` — execução permaneceu no escopo e todos os critérios congelados passaram |
| **Checkpoint de rollback** | `checkpoint/pre-f0.1-defensibility` → `758b1a59627e363534df32b2e134d309fcf50097` |
| **Checkpoint de liberação** | `checkpoint/f0.1-ready` — tag criada no commit documental que contém este dossiê |
| **Próximo passo permitido** | Implementar somente o escopo congelado abaixo; qualquer ampliação reabre o gate |

```yaml
defensibility:
  task_id: "F0.1"
  gate: "READY"
  executor: "Codex"
  authorized_at: "2026-08-03T23:51:25-03:00"
  problem_statement: >-
    O pacote não compila e ai_engineering_harness.migrations não pode ser importado porque
    check_and_migrate_manifest possui uma assinatura Python sintaticamente inválida.
  evidence:
    - command: >-
        & '<python_command>' -m compileall -q src compiler tests
      observed: >-
        exit 1; SyntaxError: Function parameters cannot be parenthesized em runner.py:15
      location: "src/ai_engineering_harness/migrations/runner.py:15"
    - command: >-
        & '<python_command>' -c "import sys; sys.path.insert(0, 'src'); import ai_engineering_harness.migrations"
      observed: >-
        exit 1; import chega a migrations.runner e falha com o mesmo SyntaxError em runner.py:15
      location: "src/ai_engineering_harness/migrations/runner.py:15"
    - command: >-
        & '<python_command>' -c "import ai_engineering_harness.migrations"
      observed: >-
        exit 1; ModuleNotFoundError porque o pacote usa layout src e ainda não está instalado;
        a aceitação congelada adiciona src ao sys.path sem ocultar falhas internas
      location: "pyproject.toml:[tool.setuptools.packages.find]"
  baseline:
    branch: "phase/f0-baseline"
    head: "758b1a59627e363534df32b2e134d309fcf50097"
    status: "clean; compileall gerou apenas caches ignorados"
    checkpoint: "checkpoint/pre-f0.1-defensibility"
  frozen_scope:
    allowed:
      - "TASK.md — transições, evidências e checkpoint"
      - "src/ai_engineering_harness/migrations/runner.py — correção sintática mínima"
      - "tests/unit/test_public_module_imports.py — novo teste de importação"
      - "src/ai_engineering_harness/**/*.py — somente correções mínimas de imports que o novo teste comprovar quebrados"
      - "C:/tmp/ai-engineering-harness-f0.1-deps — dependências declaradas usadas apenas na verificação isolada"
    excluded:
      - "mudanças de comportamento, refactors e capacidades novas"
      - "alterações em pyproject.toml, lockfile ou ambiente Python global"
      - "encoding, versionamento, documentação de produto e compilador legado"
      - "correção de integrações simuladas ou dívidas das fases 1 a 8"
  verification_environment:
    setup: >-
      & '<python_command>' -m pip install --target C:/tmp/ai-engineering-harness-f0.1-deps
      pyyaml>=6.0.1 click>=8.1.0 rich>=13.0.0 httpx>=0.27.0
    constraint: "diretório temporário fora do repositório; nenhuma instalação global"
  frozen_acceptance:
    - command: >-
        & '<python_command>' -m compileall -q src compiler tests
      expected: "exit 0 e nenhuma mensagem de erro"
    - command: >-
        & '<python_command>' -c "import sys; sys.path.insert(0, 'src'); import ai_engineering_harness.migrations"
      expected: "exit 0"
    - command: >-
        com PYTHONPATH incluindo C:/tmp/ai-engineering-harness-f0.1-deps,
        & '<python_command>' -m unittest discover -s tests/unit -p test_public_module_imports.py -v
      expected: "exit 0; todos os módulos públicos descobertos e importados; zero skips"
  rollback:
    triggers:
      - "necessidade de alterar arquivo/efeito fora do escopo congelado"
      - "sobreposição com mudança preexistente ou de outro executor"
      - "critério congelado exige ser removido ou enfraquecido"
      - "risco de perda de dados ou alteração do checkout original"
    procedure: >-
      interromper; não usar reset; antes do commit, inverter somente os hunks da F0.1 com apply_patch;
      depois do commit, usar git revert no commit exclusivo da F0.1
    verify: >-
      git status --short, git diff checkpoint/pre-f0.1-defensibility --
      src/ai_engineering_harness tests/unit e os dois comandos baseline registrados
```

#### Resultado e handoff da F0.1

| Pergunta obrigatória | Resposta |
|---|---|
| **Qual comportamento anterior foi substituído?** | O pacote deixava de compilar e `ai_engineering_harness.migrations` falhava ao importar por uma assinatura inválida. |
| **Qual é o novo contrato público?** | Nenhum contrato novo. O contrato já pretendido `MigrationRunner.check_and_migrate_manifest(self) -> bool` tornou-se Python válido e importável. |
| **Quais erros tipados podem ocorrer?** | Nenhum erro novo foi introduzido; a tarefa foi exclusivamente sintática e de smoke test. |
| **Quais side effects são produzidos?** | Nenhum side effect de produção. `compileall` cria apenas caches ignorados; dependências de verificação ficaram em `C:/tmp/ai-engineering-harness-f0.1-deps`. |
| **Onde o estado é persistido e como retoma após crash?** | Não há estado runtime nesta tarefa. Estado operacional e evidências estão neste `TASK.md` e nos checkpoints Git. |
| **Qual política autoriza a ação?** | DEC-001 e o dossiê de defensabilidade F0.1, congelado em `checkpoint/f0.1-ready`. |
| **Como secrets são protegidos?** | Não há acesso a secrets nesta tarefa. |
| **Quais eventos são emitidos?** | Nenhum evento de domínio; não aplicável à correção sintática. |
| **Quais testes provam sucesso?** | `compileall` exit 0; import de migrations exit 0; teste `unittest` importou 85 módulos públicos, sem falhas e sem skips. |
| **Quais testes provam falha segura?** | A reprodução baseline encerrou com exit 1 e identificou exatamente `runner.py:15`; como não há side effect, não existe cenário adicional de falha segura nesta tarefa. |
| **A wheel instalada externamente foi testada?** | Não; fora do escopo F0.1. Instalação reproduzível será tratada em F0.3 e wheel externa em fases posteriores. |
| **A documentação foi atualizada?** | Sim, evidências, resultado, handoff, checkpoint e próxima ação foram registrados neste arquivo. |

---

### F0.2 — Padronizar encoding

| Campo | Detalhe |
|-------|---------|
| **Status** | `completed` — critérios congelados executados e aprovados |
| **Objetivo** | Eliminar mojibake UTF-8 em todos os arquivos do projeto |
| **Arquivos envolvidos** | Todos os `.py`, `.md`, `.yaml`, `.toml`, `.json`; novo `.editorconfig` |
| **Implementação esperada** | (1) Converter todos os arquivos para UTF-8 válido; (2) corrigir strings corrompidas (`AutÃ´nomo`, `âœ”`, `Ã­ndice`); (3) remover lógica baseada em símbolos corrompidos; (4) criar `.editorconfig` com `charset = utf-8`; (5) validar CLI em Windows UTF-8 e console legado |
| **Critérios de aceite** | `rg` sem mojibake conhecido em src/docs/README; `harness --help` e `harness doctor` sem exceção |
| **Comandos de verificação** | `rg -n '\x{00C3}|\x{00E2}\x{0153}|\x{00F0}\x{0178}' src docs README.md` → exit 1, sem resultados |
| **Dependências** | F0.1 |

#### Gate de defensabilidade da F0.2

| Campo | Estado atual |
|---|---|
| **Gate** | `READY → COMPLETED` — execução permaneceu no escopo e todos os critérios congelados passaram |
| **Checkpoint de rollback** | `checkpoint/f0.1-complete` → `823406ce3f647e049bae51eb41f02e02b73e6351` |
| **Checkpoint de liberação** | `checkpoint/f0.2-ready` — tag criada no commit documental que contém este dossiê |
| **Próximo passo permitido** | Implementar somente o escopo congelado abaixo; qualquer ampliação reabre o gate |

```yaml
defensibility:
  task_id: "F0.2"
  gate: "READY"
  executor: "Codex"
  authorized_at: "2026-08-04T00:04:54-03:00"
  problem_statement: >-
    O repositório não possui configuração de editor que imponha UTF-8, o comando de busca de
    mojibake encontra os próprios exemplos literais do plano e o CLI encerra com UnicodeEncodeError
    em console OEM CP850 por emitir pontuação não representável.
  evidence:
    - command: "Test-Path -LiteralPath .editorconfig"
      observed: "False"
      location: ".editorconfig ausente"
    - command: >-
        rg -n 'Ã|âœ|ðŸ' src docs README.md
      observed: >-
        exit 0; duas ocorrências, ambas no plano: exemplos literais na linha 305 e o próprio
        comando de busca na linha 312; nenhuma ocorrência em código Python
      location: "docs/plano_implementacao_harness_operacional.md:305"
    - command: "strict UTF-8 decode de todos os arquivos rastreados .py/.md/.yaml/.yml/.toml/.json"
      observed: "INVALID_UTF8_COUNT=0"
      location: "todos os arquivos rastreados com extensões do escopo"
    - command: >-
        com PYTHONIOENCODING=cp850, & '<python_command>' -m
        ai_engineering_harness.cli.main --help e doctor
      observed: >-
        ambos exit 1; UnicodeEncodeError para U+2014 EM DASH em cli/main.py:33 e :75
      location: "src/ai_engineering_harness/cli/main.py:33"
    - command: >-
        mesmos comandos com PYTHONIOENCODING=utf-8 e cp1252
      observed: "--help e doctor exit 0 nos dois encodings"
      location: "CLI baseline"
  baseline:
    branch: "phase/f0-baseline"
    head: "823406ce3f647e049bae51eb41f02e02b73e6351"
    status: "clean"
    checkpoint: "checkpoint/f0.1-complete"
  frozen_scope:
    allowed:
      - ".editorconfig — declarar UTF-8 e regras textuais básicas"
      - "src/ai_engineering_harness/cli/main.py — substituir somente pontuação incompatível com console OEM"
      - "tests/unit/test_encoding.py — regressão de UTF-8, mojibake, .editorconfig e CLI multi-encoding"
      - "docs/plano_implementacao_harness_operacional.md — remover exemplos corrompidos literais e tornar a busca não autorreferente"
      - "TASK.md — transições, evidências, handoff e checkpoint"
    excluded:
      - "regravação em massa: todos os arquivos rastreados já são UTF-8 válido"
      - "mudança semântica dos comandos, doctor probes ou capacidades declaradas"
      - "correção de encoding fora dos arquivos em que a evidência provar falha"
      - "dependências, lockfile, versionamento, compilador e tarefas F0.3+"
  verification_environment:
    python: "python_command registrado"
    dependencies: "C:/tmp/ai-engineering-harness-f0.1-deps, somente para executar o CLI"
    constraint: "nenhuma instalação global e nenhuma alteração de manifesto"
  frozen_acceptance:
    - command: >-
        & '<python_command>' -m compileall -q src compiler tests
      expected: "exit 0"
    - command: >-
        rg -n '\x{00C3}|\x{00E2}\x{0153}|\x{00F0}\x{0178}' src docs README.md
      expected: "exit 1 e nenhuma ocorrência"
    - command: >-
        com dependências temporárias no PYTHONPATH, & '<python_command>' -m unittest
        discover -s tests/unit -p test_encoding.py -v
      expected: >-
        exit 0; todos os arquivos do escopo decodificam em UTF-8 estrito; .editorconfig impõe
        UTF-8; --help e doctor encerram com 0 em utf-8, cp1252 e cp850, sem replacement character
    - command: >-
        com dependências temporárias no PYTHONPATH, & '<python_command>' -m unittest
        discover -s tests/unit -p test_public_module_imports.py -v
      expected: "exit 0 e zero skips"
  rollback:
    triggers:
      - "necessidade de alterar arquivo fora do escopo congelado"
      - "falha exigir mudança semântica do CLI ou enfraquecimento de critério"
      - "sobreposição com mudança de outro executor"
      - "qualquer arquivo anteriormente válido tornar-se UTF-8 inválido"
    procedure: >-
      interromper; não usar reset; antes do commit, inverter apenas os hunks F0.2 com apply_patch;
      depois do commit, usar git revert no commit exclusivo da F0.2
    verify: >-
      git status --short; git diff checkpoint/f0.1-complete -- .editorconfig src/ai_engineering_harness/cli/main.py
      tests/unit/test_encoding.py docs/plano_implementacao_harness_operacional.md TASK.md; repetir o baseline
```

#### Resultado e handoff da F0.2

| Pergunta obrigatória | Resposta |
|---|---|
| **Qual comportamento anterior foi substituído?** | O repositório não impunha UTF-8, a busca de mojibake encontrava seus próprios exemplos e `--help`/`doctor` encerravam com `UnicodeEncodeError` em CP850. |
| **Qual é o novo contrato público?** | Textos rastreados do escopo devem ser UTF-8 estrito; editores recebem `charset = utf-8`; `--help` e `doctor` devem encerrar com código 0 em UTF-8, CP1252 e CP850. |
| **Quais erros tipados podem ocorrer?** | Nenhum erro público novo. O `UnicodeEncodeError` comprovado nos caminhos validados foi eliminado. |
| **Quais side effects são produzidos?** | Apenas subprocessos read-only do CLI e caches ignorados de compilação durante os testes. |
| **Onde o estado é persistido e como retoma após crash?** | Regras persistidas em `.editorconfig`; regressões em `tests/unit/test_encoding.py`; retomada pelos checkpoints Git e por este painel. |
| **Qual política autoriza a ação?** | DEC-001 e o dossiê F0.2 congelado em `checkpoint/f0.2-ready`. |
| **Como secrets são protegidos?** | Não há acesso a secrets nesta tarefa. |
| **Quais eventos são emitidos?** | Nenhum evento de domínio; não aplicável a encoding e renderização do CLI. |
| **Quais testes provam sucesso?** | Quatro testes de encoding/CLI verdes; busca de mojibake sem resultados; `compileall` e teste dos 85 módulos públicos verdes. |
| **Quais testes provam falha segura?** | Baseline CP850 provou `--help` e `doctor` com exit 1 sem efeitos persistentes; a regressão agora exige exit 0 e decodificação estrita. |
| **A wheel instalada externamente foi testada?** | Não; fora do escopo F0.2. Será coberta após o bootstrap reproduzível da F0.3. |
| **A documentação foi atualizada?** | Sim; plano e `TASK.md` não mantêm mais um critério autorreferente. |

---

### F0.3 — Tornar o ambiente reproduzível

| Campo | Detalhe |
|-------|---------|
| **Status** | `completed` — todos os critérios congelados R1/R2 e o smoke externo da wheel passaram |
| **Objetivo** | Qualquer máquina limpa consegue instalar, testar e construir o pacote com um único conjunto de comandos |
| **Arquivos envolvidos** | `pyproject.toml`, `uv.lock`, `README.md`, `.gitignore`, remoção de metadata gerada e correções mecânicas em `compiler/**/*.py`, `src/**/*.py`, `tests/**/*.py` conforme R1 |
| **Implementação esperada** | (1) Adotar `uv` como gerenciador de ambiente; (2) criar e versionar `uv.lock`; (3) completar deps dev: pytest, pytest-cov, mypy, ruff, build; (4) usar `python -m ...` nos comandos internos; (5) definir versões Python suportadas; (6) documentar bootstrap no README |
| **Critérios de aceite** | Em máquina limpa: `uv sync --all-extras` OK; `uv run python -m pytest` OK; `uv run python -m mypy src` OK; `uv run python -m ruff check .` OK; `uv run python -m build` OK |
| **Comandos de verificação** | Executar separadamente: `uv sync --all-extras`; `uv run python -m pytest`; `uv run python -m mypy src`; `uv run python -m ruff check .`; `uv run python -m build` |
| **Dependências** | F0.1, F0.2 |

#### Gate de defensabilidade da F0.3

| Campo | Estado atual |
|---|---|
| **Gate** | `READY` — ausência de ferramentas/lock reproduzida, bootstrap e rollback congelados |
| **Checkpoint de rollback** | `checkpoint/f0.2-complete` → `cda665b8352ecd73537483c922b6dcdd2956197c` |
| **Checkpoint de liberação** | `checkpoint/f0.3-ready` — tag criada no commit documental deste dossiê |
| **Autorização de ambiente** | Usuário: `continue` em 2026-08-04; limitada a `.venv`, `C:/tmp` e artefatos locais de build, sem instalação global ou perfil de shell |

```yaml
defensibility:
  task_id: "F0.3"
  gate: "READY"
  executor: "Codex"
  authorized_at: "2026-08-04T00:15:37-03:00"
  problem_statement: >-
    Uma máquina/sessão limpa não consegue instalar, testar, tipar, lintar ou construir o projeto
    pelos comandos oficiais porque uv e uv.lock não existem, as dependências dev estão incompletas
    e o README documenta somente pip install -e .
  evidence:
    - command: "Get-Command uv, python, py"
      observed: "uv=MISSING; python=MISSING; py=MISSING no PATH"
      location: "shell PowerShell da execução"
    - command: "Test-Path uv.lock; busca por *lock*"
      observed: "uv.lock=False; nenhum lockfile"
      location: "raiz do repositório"
    - command: >-
        python_command -m pytest; -m mypy src; -m ruff check .; -m build
      observed: "todos exit 1 com No module named"
      location: "runtime Python 3.12.13 registrado"
    - command: "inspeção de pyproject.toml"
      observed: >-
        extra dev contém apenas pytest e mypy; faltam pytest-cov, ruff e build;
        requires-python não possui limite/test matrix explícita
      location: "pyproject.toml"
    - command: "rg bootstrap/tooling README.md"
      observed: "somente pip install -e .; sem uv sync, testes, mypy, ruff ou build"
      location: "README.md:25"
    - command: "git ls-files src/*.egg-info/**"
      observed: "seis arquivos de metadata gerada estão versionados"
      location: "src/ai_engineering_harness.egg-info/"
  baseline:
    branch: "phase/f0-baseline"
    head: "cda665b8352ecd73537483c922b6dcdd2956197c"
    status: "clean"
    checkpoint: "checkpoint/f0.2-complete"
  frozen_decisions:
    manager: "uv"
    execution_tool: "uv 0.11.32 isolado em C:/tmp; uv_command registrado após instalação"
    project_environment: ".venv ignorado"
    cache: "C:/tmp/ai-engineering-harness-uv-cache"
    python_support: ">=3.11,<3.15; tool targets no mínimo Python 3.11"
    lock_policy: "uv.lock versionado; sync/run verificados também contra lock atualizado"
  frozen_scope:
    allowed:
      - "pyproject.toml — dependências dev, faixa Python e configuração pytest/mypy/ruff"
      - "uv.lock — lockfile gerado pelo uv"
      - "README.md — somente bootstrap, comandos de desenvolvimento e faixa Python"
      - ".gitignore — caches/build/metadata gerada"
      - "src/ai_engineering_harness.egg-info/** — remover metadata gerada versionada"
      - "src/**/*.py e tests/**/*.py — somente correções mecânicas provadas por pytest/mypy/ruff"
      - "TASK.md — transições, evidências, handoff e checkpoints"
      - ".venv, dist, build e C:/tmp — efeitos locais/ignorados de sync e verificação"
    excluded:
      - "mudança funcional, refactor arquitetural ou correção de integrações simuladas"
      - "F0.4 versionamento, F0.5 revisão de claims/links e F0.6 CI"
      - "instalação global, alteração de PATH/perfil do usuário ou download de outro Python"
      - "enfraquecer testes, mypy ou ruff para ocultar falhas comprovadas"
  frozen_acceptance:
    - command: "<uv_command> sync --all-extras"
      expected: "exit 0; projeto e deps dev instalados em .venv"
    - command: "<uv_command> lock --check"
      expected: "exit 0; pyproject e uv.lock consistentes"
    - command: "<uv_command> run python -m pytest"
      expected: "exit 0; zero testes falhando"
    - command: "<uv_command> run python -m mypy src"
      expected: "exit 0"
    - command: "<uv_command> run python -m ruff check ."
      expected: "exit 0"
    - command: "<uv_command> run python -m build"
      expected: "exit 0; sdist e wheel criadas"
    - command: "<uv_command> run python -m compileall -q src compiler tests"
      expected: "exit 0"
  rollback:
    triggers:
      - "necessidade de mudança funcional para satisfazer ferramenta"
      - "dependência requer instalação global, perfil de shell ou Python fora da faixa"
      - "critério precisa ser removido/enfraquecido ou novo arquivo sai do escopo"
      - "sync/build altera arquivo versionado não previsto"
    procedure: >-
      interromper; preservar logs; não usar reset; mover .venv para C:/tmp após validar o path;
      antes do commit inverter hunks F0.3 com apply_patch; depois do commit usar git revert
    verify: >-
      git status --short; git diff checkpoint/f0.2-complete; python_command -m compileall -q
      src compiler tests; checkpoints F0.2 continuam apontando para commits íntegros
```

#### Recongelamento F0.3-R1 — baseline real de mypy/ruff

A primeira sincronização revelou arquivos adicionais dentro do comando de aceite `ruff check .`.
Conforme a seção 4.1.3, a implementação foi interrompida antes de qualquer autofix e o escopo foi
recongelado sem remover ou enfraquecer critérios.

| Evidência | Resultado observado |
|---|---|
| `uv lock --check` | exit 0 |
| `uv run python -m pytest` | 63 testes passaram |
| `uv run python -m mypy src` | 11 erros em 7 arquivos: 5 imports YAML sem stubs, 5 atribuições em resultado heterogêneo e 1 factory mal tipada |
| `uv run python -m ruff check . --statistics` | 373 violações em 87 arquivos; 271 marcadas como safe-fix; 19 famílias de regras |

**Expansão autorizada:** `compiler/**/*.py`, `src/**/*.py` e `tests/**/*.py`, exclusivamente para
correções indicadas por mypy/ruff que preservem comportamento. `pyproject.toml` pode receber
`types-PyYAML` no extra dev. Nenhuma regra será ignorada, removida ou restringida após a falha.

**Método congelado:** criar `checkpoint/f0.3-tooling-baseline`; executar apenas
`ruff check . --fix` sem `--unsafe-fixes`; revisar o diff; corrigir manualmente apenas violações
remanescentes; repetir `pytest`, `mypy`, `ruff`, `compileall` e `build`. Qualquer correção funcional
ou alteração fora desses paths reabre o gate novamente.

#### Recongelamento F0.3-R2 — pureza dos artefatos de distribuição

Depois de todos os gates R1 passarem, o primeiro build completo revelou que o padrão amplo de
`package-data` incluiu bytecode local de `src/**/__pycache__` na wheel e no sdist. O setuptools também
registrou `ai_engineering_harness.defaults.__pycache__` como pacote ambíguo e deixou um diretório de
staging na raiz após contenção de arquivo do OneDrive. A tarefa permanece `in_progress` até o artefato
ser reconstruído sem conteúdo dependente da máquina executora.

| Evidência | Resultado observado |
|---|---|
| `uv run python -m build` após `compileall` | exit 0, porém o log adicionou `defaults/__pycache__/*.pyc` à wheel e emitiu aviso de pacote ausente da configuração |
| `git status --short` após o build | diretório gerado `ai_engineering_harness-0.1.0/` apareceu como untracked; `build/`, `dist/` e `*.egg-info` permaneceram ignorados |

**Expansão autorizada:** `pyproject.toml` pode excluir `*.pyc`, `*.pyo` e conteúdo de `__pycache__`
via `tool.setuptools.exclude-package-data`; `.gitignore` pode ignorar o staging transitório
`ai_engineering_harness-*/`. É permitida a remoção somente dos paths gerados e previamente resolvidos
dentro do workspace: `build/`, `dist/`, `src/ai_engineering_harness.egg-info/` e
`ai_engineering_harness-0.1.0/`.

**Aceite adicional congelado:** após limpar os paths gerados, repetir `compileall` e `build`; listar o
conteúdo da wheel e do sdist e exigir zero entradas contendo `__pycache__` ou terminando em `.pyc`/`.pyo`;
`git status --short` não pode exibir staging de build não ignorado. Falha nesse aceite reabre a correção,
sem ignorar o aviso no handoff.

#### Resultado e handoff da F0.3

| Verificação final | Resultado |
|---|---|
| `uv lock --check` | exit 0 |
| `uv sync --all-extras` | exit 0; `.venv` em Python 3.12.13 |
| `uv run python -m pytest` | exit 0; 63 testes passaram |
| `uv run python -m mypy src` | exit 0; sem issues em 85 arquivos |
| `uv run python -m ruff check .` | exit 0; todas as verificações passaram, sem regra ignorada e sem unsafe fix |
| `uv run python -m compileall -q src compiler tests` | exit 0 |
| `uv run python -m build` | exit 0; wheel e sdist geradas |
| inspeção wheel/sdist | 0 entradas em `__pycache__`, `.pyc` ou `.pyo` |
| instalação externa da wheel | exit 0 em `C:/tmp/ai-engineering-harness-wheel-smoke-f0.3-resume`; import carregado de `site-packages`; CLI `--help` exit 0 |

| Pergunta obrigatória | Resposta F0.3 |
|---|---|
| **Qual comportamento anterior foi substituído?** | Bootstrap ad hoc por pip, sem lock e sem toolchain completa; baseline com 11 erros mypy, 373 violações ruff e metadata gerada versionada. |
| **Qual é o novo contrato público?** | Python `>=3.11,<3.15`; `uv sync --all-extras` materializa o ambiente de `uv.lock`; testes, tipos, lint e build são executados por `uv run python -m ...`. |
| **Quais erros tipados podem ocorrer?** | Nenhum erro público novo. Falhas de lock, sync, teste, tipo, lint, compilação ou build são expostas por exit code não zero. |
| **Quais side effects são produzidos?** | `.venv`, caches uv/pytest/mypy/ruff, `build/`, `dist/`, `*.egg-info` e ambientes de smoke em `C:/tmp`; todos locais e ignorados ou externos ao repositório. |
| **Onde o estado é persistido?** | Contrato em `pyproject.toml`, resolução em `uv.lock`, instruções em `README.md`, evidências neste `TASK.md` e histórico Git. |
| **Como a operação é retomada após crash?** | Ler este painel, restaurar uv 0.11.32 isoladamente se o temporário tiver sido limpo, executar `uv sync --all-extras` e retomar de `checkpoint/f0.3-complete`. |
| **Qual política autoriza a ação?** | DEC-002, gate F0.3 `READY`, recongelamentos R1/R2 e autorização do usuário limitada a `.venv`, build e `C:/tmp`. |
| **Como secrets são protegidos?** | A tarefa não lê nem persiste secrets; downloads ocorreram apenas de índices públicos para ambiente/cache temporário. |
| **Quais eventos são emitidos?** | Nenhum evento de domínio; somente saída determinística das ferramentas de desenvolvimento. |
| **Quais testes provam sucesso?** | 63 testes, mypy em 85 arquivos, ruff integral, compileall, build limpo, inspeção dos artefatos e smoke da wheel externa. |
| **Quais testes provam falha segura?** | Baseline comprovou módulos ausentes por exit 1; smoke offline sem cache terminou com exit 1 antes de instalar parcialmente o pacote; inspeção R2 falharia com qualquer bytecode no artefato. |
| **A wheel instalada externamente foi testada?** | Sim; versão `0.1.0`, import a partir do `site-packages` temporário e `harness --help` com exit 0. |
| **A documentação foi atualizada?** | Sim; bootstrap no `README.md`, decisões/evidências/handoff neste `TASK.md` e configuração declarativa no `pyproject.toml`. |

---

### F0.4 — Unificar versionamento

| Campo | Detalhe |
|-------|---------|
| **Status** | `completed` — package version única, schemas separados e todos os critérios congelados passaram |
| **Objetivo** | Uma única fonte de versão do pacote; schemas versionados separadamente |
| **Arquivos envolvidos** | `pyproject.toml`, `src/ai_engineering_harness/__init__.py`, schemas de grafo/artifact/policy |
| **Implementação esperada** | (1) `__version__` via `importlib.metadata.version`; (2) separar `package_version`, `graph_schema_version`, `artifact_schema_version`, `policy_schema_version`; (3) remover versões conflitantes (`0.1.0`, `1.0.0`, `3.2.0`) usadas para a mesma coisa |
| **Critérios de aceite** | `harness --version`, metadata da wheel e `ai_engineering_harness.__version__` são idênticos; schemas com compatibilidade testada separadamente |
| **Comandos de verificação** | `harness --version` e o `python_command` registrado com `-c "import ai_engineering_harness; print(ai_engineering_harness.__version__)"` |
| **Dependências** | F0.1, F0.3 |

#### Gate de defensabilidade da F0.4

| Campo | Estado atual |
|---|---|
| **Gate** | `READY` — duplicação do pacote e ambiguidade dos schemas comprovadas; escopo, aceite e rollback congelados |
| **Checkpoint de rollback** | `checkpoint/f0.3-complete` → `517b9e0285b70e65d7839452575f3c370174a35f` |
| **Checkpoint de liberação** | `checkpoint/f0.4-ready` — tag a ser criada no commit documental deste dossiê antes da primeira edição de implementação |

```yaml
defensibility:
  task_id: "F0.4"
  gate: "READY"
  executor: "Codex"
  authorized_at: "2026-08-04T00:47:55-03:00"
  problem_statement: >-
    A versão 0.1.0 coincide hoje nas superfícies públicas, mas está copiada manualmente em quatro
    pontos; versões 1.0, 1.0.0 e 3.2.0 aparecem em artefato, grafos e políticas sem namespaces
    explícitos, permitindo drift e comparações entre conceitos diferentes.
  evidence:
    - command: "rg de __version__, version options e constantes"
      observed: >-
        pyproject.toml, __init__.py, click.version_option e GraphCompiler.HARNESS_VERSION mantêm
        literais 0.1.0 independentes; runtime_adapter_version repete o mesmo literal
      location: "pyproject.toml; src/ai_engineering_harness/{__init__.py,cli/main.py,compiler/compiler.py}"
    - command: ".venv/Scripts/python -c metadata/__version__; harness --version"
      observed: "todos imprimem 0.1.0 e CLI exit 0, mas por duplicação não vinculada"
      location: "ambiente F0.3"
    - command: "rg de schema/version em compiler, defaults e testes"
      observed: >-
        artifact_schema_version=1.0 no compilador oficial, maf_schema_version=1.0.0 no legado,
        graph/policy version=3.2.0 e profile version=1.0; não há graph_schema_version nem
        policy_schema_version explícitos
      location: "compiler/compile.py; src/ai_engineering_harness/compiler/compiler.py; defaults/**/*.yaml"
  baseline:
    branch: "phase/f0-baseline"
    head: "517b9e0285b70e65d7839452575f3c370174a35f"
    status: "clean"
    checkpoint: "checkpoint/f0.3-complete"
  frozen_decisions:
    package_version: >-
      pyproject.toml permanece fonte autoral 0.1.0; runtime lê a metadata instalada por
      importlib.metadata.version sem fallback literal
    graph_schema_version: "1.0; separado da definition_version 3.2.0 dos grafos padrão"
    artifact_schema_version: "1.0; igual nos compiladores oficial e legado"
    policy_schema_version: "1.0; separado da definition_version 3.2.0 das políticas padrão"
    compatibility: "comparação exata por namespace nesta fase; evolução backward-compatible será definida na F1/F5"
  frozen_scope:
    allowed:
      - "pyproject.toml e uv.lock — somente consistência da metadata/lock, sem mudar 0.1.0 ou dependências"
      - "src/ai_engineering_harness/versioning.py — constantes separadas e leitura da metadata instalada"
      - "src/ai_engineering_harness/__init__.py e cli/main.py — expor a mesma package version"
      - "src/ai_engineering_harness/compiler/compiler.py e compiler/compile.py — consumir package/artifact schema version sem literal duplicado"
      - "src/ai_engineering_harness/defaults/graphs/*.yaml — graph_schema_version e definition_version explícitos"
      - "src/ai_engineering_harness/defaults/policies/*.yaml — policy_schema_version e definition_version explícitos"
      - "tests/unit/test_packaging.py, tests/unit/test_phase5.py e tests/unit/test_versioning.py — regressões das quatro superfícies"
      - "README.md e TASK.md — contrato, evidências, handoff e checkpoints"
      - "build, dist, *.egg-info, .venv e C:/tmp — efeitos ignorados/temporários de verificação"
    excluded:
      - "mudar package version 0.1.0, adicionar dependência ou alterar faixa Python"
      - "unificar os dois compiladores, criar modelos GraphSpec/PolicySpec ou implementar migração de schema (F1/F5)"
      - "reinterpretar versões de agent, tool, profile ou observability; pertencem às fases dos respectivos contratos"
      - "alterar comportamento do runtime, providers, gates, promoção ou rollback"
  frozen_acceptance:
    - command: "<uv_command> lock --check; <uv_command> sync --all-extras"
      expected: "ambos exit 0; uv.lock permanece consistente"
    - command: "<uv_command> run python -m pytest"
      expected: "exit 0; 63+ testes, incluindo compatibilidade separada das versões"
    - command: "<uv_command> run python -m mypy src; <uv_command> run python -m ruff check ."
      expected: "ambos exit 0; nenhuma regra reduzida ou ignorada"
    - command: "<uv_command> run python -m compileall -q src compiler tests; <uv_command> run python -m build"
      expected: "ambos exit 0; wheel e sdist sem bytecode"
    - command: "instalar wheel em venv C:/tmp e comparar importlib.metadata, __version__ e harness --version"
      expected: "três valores exatamente iguais a 0.1.0 e import originado de site-packages"
    - command: "testes carregam todos os defaults graphs/policies e compilam um artefato"
      expected: >-
        graph_schema_version=1.0, artifact_schema_version=1.0 e policy_schema_version=1.0;
        definition_version=3.2.0 permanece independente
  rollback:
    triggers:
      - "import do pacote exigir fallback literal ou falhar após uv sync/wheel install"
      - "consumer atual depender do campo genérico version e não puder migrar no escopo"
      - "necessidade de unificar compiladores ou implementar migração backward-compatible agora"
      - "metadata, CLI e __version__ divergirem ou qualquer gate F0.3 regredir"
    procedure: >-
      interromper e preservar logs; antes do commit inverter hunks F0.4 por apply_patch; após o
      commit usar git revert; nunca reset; preservar checkpoint/f0.3-complete
    verify: >-
      git status --short; git diff checkpoint/f0.3-complete; uv lock --check; uv run python -m pytest;
      metadata, __version__ e harness --version retornam ao baseline 0.1.0
```

#### Resultado e handoff da F0.4

| Verificação final | Resultado |
|---|---|
| `uv lock --check` e `uv sync --all-extras` | ambos exit 0; lock permaneceu consistente e sem nova dependência |
| `uv run python -m pytest` | exit 0; 65 testes passaram |
| `uv run python -m mypy src` | exit 0; sem issues em 86 arquivos |
| `uv run python -m ruff check .` | exit 0; todas as verificações passaram |
| `uv run python -m compileall -q src compiler tests` | exit 0 |
| `uv run python -m build` | exit 0; wheel e sdist; 0 entradas de bytecode; `versioning.py` presente na wheel |
| wheel instalada em ambiente externo | metadata=`0.1.0`; `__version__`=`0.1.0`; CLI=`harness, version 0.1.0`; import de `site-packages` |
| schemas na wheel externa | graph=`1.0`; artifact=`1.0`; policy=`1.0` |
| compilador legado | exit 0; emitiu `artifact_schema_version=1.0` e `package_version=0.1.0` |
| buscas de duplicação | nenhum literal independente em `__version__`, CLI, compiler/runtime adapter; nenhum `maf_schema_version` legado |

| Pergunta obrigatória | Resposta F0.4 |
|---|---|
| **Qual comportamento anterior foi substituído?** | Quatro literais independentes de package version e campos genéricos `version` em grafos/políticas; o compilador legado emitia schema `1.0.0` enquanto o oficial emitia `1.0`. |
| **Qual é o novo contrato público?** | `pyproject.toml` é a única fonte autoral do pacote; `PACKAGE_VERSION` lê a distribuição instalada; `__version__` e CLI a reutilizam. Grafos/políticas expõem schema `1.0` e definition `3.2.0` separadamente; artefatos expõem package/schema explicitamente. |
| **Quais erros tipados podem ocorrer?** | `importlib.metadata.PackageNotFoundError` quando alguém importa o pacote sem instalar a distribuição; esse caminho não recebe fallback literal e o bootstrap oficial exige `uv sync`. |
| **Quais side effects são produzidos?** | Somente caches, build/sdist/wheel e venv de smoke em `C:/tmp`; o JSON de prova do compilador legado foi removido após validação. |
| **Onde o estado é persistido?** | Package version em `pyproject.toml`/metadata; namespaces em `versioning.py`; versões serializadas nos YAMLs padrão; evidências neste painel e no Git. |
| **Como a operação é retomada após crash?** | Retomar de `checkpoint/f0.4-complete`; reinstalar/sincronizar por uv se metadata não estiver disponível; reexecutar os testes de versionamento antes de nova alteração. |
| **Qual política autoriza a ação?** | DEC-003, dossiê F0.4 `READY` e `checkpoint/f0.4-ready`. |
| **Como secrets são protegidos?** | Nenhum secret é lido ou persistido por versionamento, build ou testes. |
| **Quais eventos são emitidos?** | Nenhum evento de domínio; somente saída dos comandos de validação. |
| **Quais testes provam sucesso?** | `test_packaging`, `test_phase5`, `test_versioning`, suíte integral, compilador legado, build inspecionado e wheel externa. |
| **Quais testes provam falha segura?** | Testes rejeitam divergência metadata/import/CLI, campo genérico `version`, schema incompatível e ausência dos defaults; import sem distribuição falha em vez de inventar versão. |
| **A wheel instalada externamente foi testada?** | Sim; ambiente `C:/tmp/ai-engineering-harness-wheel-smoke-f0.4`, instalação offline, import/CLI/metadata/schemas aprovados. |
| **A documentação foi atualizada?** | Sim; contrato em `README.md` e estado/decisão/handoff neste `TASK.md`. |

---

### F0.5 — Corrigir documentação de estado

| Campo | Detalhe |
|-------|---------|
| **Status** | `completed` — documentação alinhada ao estado real; todos os critérios congelados passaram |
| **Objetivo** | Documentação não deve declarar capacidades inexistentes nem conter links quebrados |
| **Arquivos envolvidos** | `README.md`, `docs/*.md` |
| **Implementação esperada** | (1) Substituir "Em Produção" por "Protótipo / Em desenvolvimento"; (2) remover referências a arquivos inexistentes; (3) corrigir links `file:///` absolutos; (4) criar matriz Capacidade/Implementada/Experimental/Planejada; (5) marcar adapters fake como dívida técnica |
| **Critérios de aceite** | Nenhum documento declara produção; nenhum link aponta para arquivo inexistente |
| **Comandos de verificação** | `rg "Em Produção" docs README.md` → sem resultados |
| **Dependências** | F0.1 |

#### Gate de defensabilidade da F0.5

| Campo | Estado atual |
|---|---|
| **Gate** | `READY → COMPLETED` — execução permaneceu no escopo e todos os critérios congelados passaram |
| **Checkpoint de rollback** | `checkpoint/f0.4-complete` → `aaee725f226f363b6c3636a5d8b746379d41b594` |
| **Checkpoint de liberação** | `checkpoint/f0.5-ready` — tag criada no commit documental deste dossiê antes da correção dos documentos |

```yaml
defensibility:
  task_id: "F0.5"
  gate: "READY"
  executor: "Codex"
  authorized_at: "2026-08-04T01:16:15-03:00"
  problem_statement: >-
    README e documentos descrevem o projeto como autônomo, pronto e totalmente funcional, mas o
    runtime ainda usa providers que fabricam respostas, doctor que sempre retorna saudável,
    Codebase-Memory simulado, promoção com SHA sintético e terminal com shell implícito. Existem
    também nove links locais absolutos e referências a paths ausentes do repositório.
  evidence:
    - command: >-
        rg -n "Em Produção|100% OPERACIONAL|100% Funcional|100% funcional|totalmente revisado|altamente robusto"
        README.md docs --glob '*.md'
      observed: >-
        exit 0; claims positivos em harness_architecture_spec.md, walkthrough.md,
        walkthrough_audit.md, agentic_lifecycle_audit.md e audit_report.md; o plano ainda contém o
        próprio literal proibido no critério F0.5
      location: "README.md e docs/*.md"
    - command: "rg -n 'file:///' README.md docs --glob '*.md'"
      observed: >-
        exit 0; nove URLs absolutas: quatro no README, duas em audit_report.md e três em walkthrough.md;
        o plano contém ainda o próprio padrão do critério
      location: "README.md; docs/{audit_report.md,walkthrough.md,plano_implementacao_harness_operacional.md}"
    - command: >-
        Test-Path contracts, policies, graphs/specs e
        src/ai_engineering_harness/observability/log_integrity.py
      observed: "todos False; documentos apresentam esses paths como estrutura atual"
      location: "docs/{audit_report.md,walkthrough.md,walkthrough_audit.md}"
    - command: >-
        rg -n "mock_ast|is_healthy=True|synthetic_sha|shell=True|dry_run=True|Response to:" src --glob '*.py'
      observed: >-
        exit 0; providers retornam texto fabricado, doctor retorna healthy incondicionalmente,
        indexador persiste mock_ast, runtime força dry_run e promoção devolve synthetic_sha;
        TerminalAdapter executa string com shell=True
      location: >-
        src/ai_engineering_harness/{models/adapters,doctor/probes.py,indexer/codebase_memory_adapter.py,
        runtime/{engine.py,promotion_manager.py},tools/adapters/terminal.py}
    - command: >-
        com temporários confinados em build/f0.5-baseline,
        .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp build/f0.5-baseline/pytest
      observed: >-
        exit 0; 65 testes e 6 subtests passaram. A primeira execução fora do confinamento falhou por
        PermissionError do sandbox; um diretório gerado graphs/compiled, vazio e ignorado, foi removido
        após inspeção para restaurar o baseline estrutural
      location: "ambiente de verificação; nenhum arquivo rastreado alterado"
  baseline:
    branch: "phase/f0-baseline"
    head: "aaee725f226f363b6c3636a5d8b746379d41b594"
    status: "clean; somente artefatos ignorados de teste/build; graphs/compiled vazio foi removido"
    checkpoint: "checkpoint/f0.4-complete"
  frozen_decisions:
    capability_matrix:
      implemented:
        - "empacotamento, bootstrap de desenvolvimento e comandos de qualidade reproduzíveis"
        - "versionamento único do pacote e namespaces separados de schema"
      experimental:
        - "CLI, compiladores, FSM, contexto, plano, verificação, auditoria e aprovações locais"
        - "interfaces de providers, Serena, Codebase-Memory, doctor, promoção, worktree e rollback"
      planned:
        - "providers e MCPs reais, isolamento Git, promoção/reversão reais, recovery e segurança fail-closed"
        - "CI Windows/Linux e instalação externa segura para uso cotidiano em IDE/CLI"
    wording: >-
      arquitetura-alvo será descrita como projetada/planejada; comportamento existente só será
      chamado implementado quando houver efeito real e teste correspondente; simulações serão
      identificadas como dívida técnica sem eufemismo
  frozen_scope:
    allowed:
      - "README.md — status honesto, matriz de capacidade, uso seguro e links relativos"
      - "docs/*.md — corrigir claims, estado, paths e links; preservar requisitos futuros do plano"
      - "tests/unit/test_documentation.py — regressões de claims, links locais e estrutura Markdown"
      - "TASK.md — transições, evidências, handoff e checkpoints"
      - "build/f0.5-* — temporários ignorados e confinados para verificação"
    excluded:
      - "qualquer alteração em src/, compiler/, pyproject.toml ou uv.lock"
      - "implementar ou corrigir adapters, doctor, runtime, promoção, worktree, rollback ou gates"
      - "reescrever requisitos futuros do plano como se já estivessem entregues"
      - "alterar docs/walkthrough_dashboard.html ou adicionar dependência de Markdown"
  frozen_acceptance:
    - command: "rg -n 'Em Produção' docs README.md"
      expected: "exit 1 e nenhuma ocorrência, inclusive autorreferência do plano"
    - command: "rg -n 'file:///' docs README.md"
      expected: "exit 1 e nenhuma ocorrência, inclusive autorreferência do plano"
    - command: >-
        .venv/Scripts/python.exe -m pytest tests/unit/test_documentation.py
        tests/unit/test_encoding.py -q -p no:cacheprovider --basetemp build/f0.5-doc-pytest
      expected: >-
        exit 0; matriz presente; nenhum claim positivo proibido; links relativos resolvem;
        nenhum link local absoluto; todos os Markdown UTF-8 terminam com newline e possuem fences balanceadas
    - command: >-
        com LOCALAPPDATA/TEMP/TMP confinados em build/f0.5-full,
        .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp build/f0.5-full/pytest
      expected: "exit 0; 65+ testes e todos os subtests passam"
    - command: >-
        .venv/Scripts/python.exe -m ruff check .;
        .venv/Scripts/python.exe -m compileall -q src compiler tests;
        git diff --check
      expected: "todos exit 0; nenhuma regra reduzida e nenhum erro de whitespace/compilação"
  rollback:
    triggers:
      - "documento precisar declarar uma simulação como capacidade operacional"
      - "correção exigir alteração de runtime ou arquivo fora do escopo congelado"
      - "link local não puder ser resolvido de forma portátil"
      - "qualquer gate F0.4 ou critério documental congelado regredir"
    procedure: >-
      interromper e preservar evidências; antes do commit inverter somente hunks F0.5 por apply_patch;
      depois do commit usar git revert no commit exclusivo F0.5; nunca reset; preservar
      checkpoint/f0.4-complete
    verify: >-
      git status --short; git diff checkpoint/f0.4-complete; repetir os testes documentais,
      a suíte completa confinada, ruff, compileall e as duas buscas sem resultado
```

#### Resultado e handoff da F0.5

| Verificação final | Resultado |
|---|---|
| Busca do rótulo positivo de estado em `docs README.md` | exit 1; nenhuma ocorrência |
| Busca de URLs locais absolutas em `docs README.md` | exit 1; nenhuma ocorrência |
| Testes `test_documentation.py` + `test_encoding.py` | exit 0; 8 testes + 6 subtests passaram |
| Suíte integral com temporários confinados | exit 0; 69 testes + 6 subtests passaram |
| Links Markdown locais | todos relativos e existentes; zero alvo ausente |
| Estrutura Markdown | UTF-8 estrito, newline final e fences balanceadas em README + 8 documentos |
| `mypy src` | exit 0; sem issues em 86 arquivos |
| `ruff check .`, `compileall` e `git diff --check` | todos exit 0 |

| Pergunta obrigatória | Resposta F0.5 |
|---|---|
| **Qual comportamento anterior foi substituído?** | README/docs misturavam arquitetura futura com entrega atual, afirmavam estado operacional, mantinham contagens antigas, nove URLs dependentes da máquina e árvores com paths inexistentes. |
| **Qual é o novo contrato público?** | O projeto é apresentado como protótipo; toda capacidade é classificada como implementada, experimental/simulada ou planejada; links locais são relativos e devem resolver no clone. |
| **Quais erros tipados podem ocorrer?** | Nenhum erro de runtime novo; tarefa documental. A regressão falha por assertion explícita quando claim proibido, link absoluto/quebrado ou Markdown estruturalmente inválido reaparece. |
| **Quais side effects são produzidos?** | Alterações somente em Markdown e teste documental; pytest/compileall criaram apenas temporários/caches ignorados em `build/f0.5-*`. |
| **Onde o estado é persistido?** | Contrato de status no README/docs; regressões em `test_documentation.py`; evidências/checkpoints neste painel e no Git. |
| **Como a operação é retomada após crash?** | Retomar de `checkpoint/f0.5-complete`; reexecutar os dois testes documentais e as buscas antes de preparar F0.6. |
| **Qual política autoriza a ação?** | DEC-001, DEC-004, dossiê F0.5 `READY` e `checkpoint/f0.5-ready`. |
| **Como secrets são protegidos?** | Nenhum secret foi lido, impresso ou persistido. |
| **Quais eventos são emitidos?** | Nenhum evento de domínio; somente saída dos gates de documentação e qualidade. |
| **Quais testes provam sucesso?** | Quatro regressões documentais, encoding multi-console, suíte integral, link resolution, ruff, mypy, compileall e diff check. |
| **Quais testes provam falha segura?** | O baseline reproduziu claims e nove URLs; o novo teste bloqueia regressão antes de merge e não executa qualquer side effect de produto. |
| **A wheel instalada externamente foi testada?** | Não foi reconstruída nesta tarefa documental; o smoke externo aprovado na F0.4 permanece o baseline. |
| **A documentação foi atualizada?** | Sim; README, sete documentos de estado/auditoria e o critério autorreferente do plano foram alinhados. |

---

### F0.6 — Criar CI mínima

| Campo | Detalhe |
|-------|---------|
| **Status** | `completed` — CI Windows/Linux verde antes e depois do merge; `main` protegida; bloqueio/restauração comprovados em PR separado |
| **Objetivo** | Pipeline automatizado impede merge com falhas em encoding, lint, tipos, testes ou build |
| **Arquivos envolvidos** | `.github/workflows/*.yml` (ou equivalente CI) |
| **Implementação esperada** | Pipeline Windows + Linux com jobs: encoding/compileall; ruff; mypy; testes unitários; E2E locais; build da wheel; instalação e smoke test. Merge bloqueado quando job obrigatório falha |
| **Critérios de aceite** | Pipeline verde em Windows e Linux; PR com erro em job obrigatório é bloqueado |
| **Comandos de verificação** | Execução local (`act`) ou validação manual na CI escolhida |
| **Dependências** | F0.1, F0.2, F0.3, F0.4, F0.5 |

#### Gate de defensabilidade da F0.6

| Campo | Estado atual |
|---|---|
| **Gate** | `CORRECTION_REMOTE_VALIDATED → COMPLETED` — 11/11 jobs verdes; `CI required` obrigatório; falha controlada bloqueou merge e o revert restaurou estado verde |
| **Checkpoint de rollback** | `checkpoint/f0.5-complete` → `7cd6d81137b64914b8f53f6067f76f42cfde2711` |
| **Checkpoint de liberação** | `checkpoint/f0.6-ready` — tag criada no commit deste dossiê antes do primeiro workflow |
| **Fronteira externa** | PR principal `#1` mesclado sem bypass; `main` exige `CI required` em modo estrito inclusive para administradores; PR de prova `#2` fechado sem merge; tags remotas não foram alteradas |

```yaml
defensibility:
  task_id: "F0.6"
  gate: "READY"
  executor: "Codex"
  authorized_at: "2026-08-04T01:36:40-03:00"
  problem_statement: >-
    O repositório não possui workflow rastreado, portanto lint, tipos, testes, build e smoke dependem
    exclusivamente de execução manual e nenhum check pode bloquear merge no GitHub.
  evidence:
    - command: "Test-Path .github/workflows; git ls-files '.github/workflows/*'"
      observed: "False; zero arquivo rastreado"
      location: ".github/workflows ausente"
    - command: "git remote -v; git branch --show-current"
      observed: >-
        origin=https://github.com/Wf-ops1/Harnessinfra.git; branch local phase/f0-baseline;
        nenhum push executado
      location: ".git/config e refs locais"
    - command: "uv --version; uv lock --check; uv sync --all-extras --locked"
      observed: "uv 0.11.32; todos exit 0; 35 packages resolvidos e 34 verificados"
      location: "build/f0.6-tools/uv/bin/uv.exe; .venv; uv.lock"
    - command: "Get-Command act, gh"
      observed: "ambos ausentes; validação remota não pode ser substituída localmente por act/gh"
      location: "shell da execução"
    - command: "inspeção oficial de releases/documentação em 2026-08-04"
      observed: >-
        actions/checkout v6.0.2=de0fac2e4500dabe0009e67214ff5f5447ce83dd;
        actions/setup-python v6.2.0=a309ff8b426b58ec0e2a45f0f869d46889d02405;
        astral-sh/setup-uv v8.1.0=08807647e7069bb48b6ef5acd8ec9567f424441b;
        GitHub exige merge_group para required checks usados com merge queue
      location: >-
        github.com/actions/{checkout,setup-python}/releases;
        github.com/astral-sh/setup-uv; docs.github.com required status checks
  baseline:
    branch: "phase/f0-baseline"
    head: "7cd6d81137b64914b8f53f6067f76f42cfde2711"
    status: "clean; somente ambientes/temporários ignorados em build/"
    checkpoint: "checkpoint/f0.5-complete"
  frozen_decisions:
    provider: "GitHub Actions"
    workflow: ".github/workflows/ci.yml"
    permissions: "contents: read; checkout persist-credentials=false"
    triggers:
      push: ["main", "phase/**"]
      pull_request: ["main"]
      merge_group: true
      workflow_dispatch: true
    actions:
      checkout: "de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6.0.2"
      setup_python: "a309ff8b426b58ec0e2a45f0f869d46889d02405 # v6.2.0"
      setup_uv: "08807647e7069bb48b6ef5acd8ec9567f424441b # v8.1.0"
      uv_version: "0.11.32"
    jobs:
      quality:
        os: ["ubuntu-latest", "windows-latest"]
        python: ["3.11", "3.14"]
        gates: ["lock/sync", "encoding/docs", "compileall", "ruff", "mypy"]
      tests:
        os: ["ubuntu-latest", "windows-latest"]
        python: ["3.11", "3.14"]
        gates: ["unit", "e2e"]
      package:
        os: ["ubuntu-latest", "windows-latest"]
        python: ["3.12"]
        gates: ["build", "wheel bytecode inspection", "isolated install/import/CLI smoke"]
      aggregate:
        name: "CI required"
        contract: "always runs and fails unless quality, tests and package all succeeded"
    branch_protection: >-
      main exige o check estável CI required, strict=true e enforce_admins=true; force-push e exclusão
      permanecem desabilitados; nenhuma exigência adicional de review foi introduzida
  frozen_scope:
    allowed:
      - ".github/workflows/ci.yml — workflow GitHub Actions"
      - "tests/ci/smoke_wheel.py — smoke isolado e inspeção de artefato cross-platform"
      - "tests/unit/test_ci_workflow.py — estrutura, matrizes, triggers e pins do workflow"
      - "README.md — atualizar somente estado da CI e comando de smoke"
      - "TASK.md — transições, evidências, handoff e checkpoints"
      - "build/f0.6-*; build/; dist/ — efeitos ignorados de ferramentas e validação"
    excluded:
      - "src/, compiler/, pyproject.toml, uv.lock e dependências"
      - "alterar testes existentes ou reduzir gates para acomodar a CI"
      - "secrets, publishing, deploy, release e caches de terceiros"
      - "push, criação de PR, alteração de main ou branch protection sem autorização explícita"
  frozen_acceptance:
    - command: "uv lock --check; uv sync --all-extras --locked"
      expected: "ambos exit 0; lockfile não muda"
    - command: >-
        uv run python -m pytest tests/unit/test_ci_workflow.py
        tests/unit/test_documentation.py tests/unit/test_encoding.py -q
      expected: >-
        exit 0; YAML parseia; triggers, permissions, matrizes, jobs, aggregate e três actions por SHA
        exato são obrigatórios
    - command: "uv run python -m build; uv run python tests/ci/smoke_wheel.py"
      expected: >-
        ambos exit 0; uma wheel sem bytecode instala em ambiente uv isolado; metadata, __version__,
        origem externa e CLI coincidem
    - command: >-
        uv run python -m pytest; uv run python -m mypy src; uv run python -m ruff check .;
        uv run python -m compileall -q src compiler tests; git diff --check
      expected: "todos exit 0; nenhuma regra ou teste enfraquecido"
    - command: "GitHub Actions no commit remoto, push/PR/merge_group"
      expected: >-
        quality, tests e package verdes em ubuntu-latest e windows-latest; CI required verde somente
        quando todas as dependências tiverem sucesso
    - command: "branch protection de main"
      expected: "CI required configurado como required status check; PR com falha não pode ser mesclado"
  rollback:
    triggers:
      - "workflow exige secret, permissão de escrita ou action não pinada"
      - "Windows/Linux divergem sem causa reproduzida e registrada"
      - "smoke importa o checkout ou aceita bytecode no artefato"
      - "qualquer job pode falhar/ser cancelado e CI required ainda passar"
      - "critério local ou remoto precisar ser enfraquecido"
    procedure: >-
      interromper; antes do commit inverter apenas hunks F0.6 por apply_patch; depois do commit usar
      git revert; se já houver push, publicar o revert por fluxo autorizado; nunca editar branch
      protection antes de um check real existir
    verify: >-
      git status --short; git diff checkpoint/f0.5-complete; repetir gates locais; no GitHub confirmar
      que o workflow/regras voltaram ao último estado conhecido
```

#### Recongelamento F0.6-R1 — shebang e bit executável no Linux

O primeiro run remoto da F0.6 comprovou uma divergência objetiva que o filesystem Windows não
consegue reproduzir: `compiler/compile.py` começa com shebang, mas o índice Git o publicou com modo
`100644`. O Ruff 0.16.1 aplica `EXE001` no Ubuntu e encerra o job de lint com exit 1.

| Campo | Decisão congelada |
|---|---|
| **Problema comprovado** | Run `30878935976`, jobs Ubuntu `91895938462` (Python 3.11) e `91895938420` (Python 3.14): etapa `Lint` falhou com `EXE001 Shebang is present but file is not executable` em `compiler/compile.py:1:1` |
| **Comportamento preservado** | Conteúdo Python, shebang, CLI do compilador, regras Ruff, matriz Windows/Linux e todos os demais gates permanecem inalterados |
| **Escopo adicional permitido** | Somente metadata Git de `compiler/compile.py`, de `100644` para `100755`, e este registro em `TASK.md` |
| **Explicitamente proibido** | Remover o shebang; adicionar `noqa`; ignorar `EXE001`; excluir `compiler/`; retirar Ubuntu; reduzir matriz ou gates |
| **Critério local** | `git ls-files --stage compiler/compile.py` mostra `100755`; blob/hash do conteúdo não muda; Ruff, testes focados e `git diff --check` permanecem verdes |
| **Critério remoto** | Novo run no commit corrigido conclui os 4 quality, 4 tests, 2 package e `CI required` com `success` |
| **Rollback** | Antes do commit: `git update-index --chmod=-x compiler/compile.py`; depois do commit/push: `git revert <commit-da-correção>` pelo mesmo fluxo autorizado |

Evidência remota: <https://github.com/Wf-ops1/Harnessinfra/actions/runs/30878935976>.

#### Recongelamento F0.6-R2 — prova controlada de branch protection

A existência da regra remota não prova, isoladamente, que um merge é bloqueado quando o check
obrigatório falha. A prova será executada em PR e branch separados, sem merge e sem alteração direta
de `main`.

| Campo | Decisão congelada |
|---|---|
| **Problema a provar** | `main` deve recusar merge quando `CI required` não conclui com `success`, inclusive para administrador |
| **Branch/PR de prova** | `proof/f0.6-required-check` partindo do HEAD verde de `phase/f0-baseline`, em PR separado para `main` |
| **Falha permitida** | Adicionar somente `tests/unit/test_ci_required_block.py`, com um teste que falha de forma intencional e identificável |
| **Explicitamente proibido** | Alterar workflow, matriz, código de produto, testes existentes ou proteção para fabricar o resultado; realizar merge; fazer push direto em `main`; usar bypass administrativo |
| **Critério de bloqueio** | Jobs de testes e aggregate `CI required` falham; PR informa estado não mesclável/bloqueado enquanto o check obrigatório está vermelho |
| **Restauração obrigatória** | Reverter o commit de falha na própria branch de prova, publicar o revert e exigir novo run integralmente verde |
| **Fechamento da prova** | Confirmar PR novamente liberado pelos checks, fechar o PR sem merge e preservar URLs/commits como evidência |
| **Rollback** | `git revert <commit-de-falha>`; se a regra remota divergir do contrato, interromper e restaurar a proteção anterior antes de continuar |

#### Resultado local e handoff parcial da F0.6

| Verificação local | Resultado |
|---|---|
| `uv lock --check` e `uv sync --all-extras --locked` | ambos exit 0; lock permaneceu consistente |
| Contrato do workflow + documentação + encoding | exit 0; 12 testes + 6 subtests passaram |
| Suíte integral | exit 0; 73 testes + 6 subtests passaram |
| `mypy src` | exit 0; sem issues em 86 arquivos |
| `ruff check .`, `compileall` e `git diff --check` | todos exit 0 |
| Build | exit 0; wheel e sdist geradas |
| Smoke isolado da wheel | exit 0; metadata=`0.1.0`, package=`0.1.0`, CLI=`harness, version 0.1.0`; import fora do checkout |
| Contrato CI | quality/tests em Windows+Linux e Python 3.11/3.14; package em ambos SOs/Python 3.12; actions pinadas; `CI required` fail-closed |

| Primeiro run remoto | Resultado |
|---|---|
| Run | [`30878935976`](https://github.com/Wf-ops1/Harnessinfra/actions/runs/30878935976), commit `56b104fd1158bd3af35de28f686140b65b61c5ac` |
| Testes | 4/4 jobs `success` em Ubuntu/Windows e Python 3.11/3.14 |
| Pacote | 2/2 jobs `success` em Ubuntu/Windows e Python 3.12, incluindo build e smoke da wheel |
| Qualidade Windows | 2/2 jobs `success` em Python 3.11/3.14 |
| Qualidade Ubuntu | 2/2 jobs `failure` somente no lint: `EXE001` em `compiler/compile.py:1:1` |
| Aggregate | `CI required` concluiu `failure`, provando comportamento fail-closed quando quality falha |

| Run corretivo remoto | Resultado |
|---|---|
| Run | [`30879368468`](https://github.com/Wf-ops1/Harnessinfra/actions/runs/30879368468), commit `3d465680a085ba6c51aee18e38def3858a14d4c1` |
| Qualidade | 4/4 jobs `success` em Ubuntu/Windows e Python 3.11/3.14; `EXE001` eliminado pelo modo `100755` |
| Testes | 4/4 jobs `success` em Ubuntu/Windows e Python 3.11/3.14 |
| Pacote | 2/2 jobs `success` em Ubuntu/Windows e Python 3.12, incluindo build e smoke da wheel |
| Aggregate | `CI required` concluiu `success`; run completo `completed/success`, 11/11 jobs verdes |

| Proteção e prova remota | Resultado |
|---|---|
| PR principal | [`#1`](https://github.com/Wf-ops1/Harnessinfra/pull/1), mesclado sem bypass por merge commit `3f29c4c894808eb47464c96a01c9048198d971c9`; fechamento ancorado por `checkpoint/f0.6-complete` |
| CI do PR principal | Runs [`30879923860`](https://github.com/Wf-ops1/Harnessinfra/actions/runs/30879923860) (push) e [`30879926143`](https://github.com/Wf-ops1/Harnessinfra/actions/runs/30879926143) (pull request), ambos `completed/success` |
| CI pós-merge em `main` | Run [`30917066077`](https://github.com/Wf-ops1/Harnessinfra/actions/runs/30917066077), commit `3f29c4c894808eb47464c96a01c9048198d971c9`, 11/11 jobs `success`, incluindo `CI required` |
| Proteção de `main` | `CI required` obrigatório; `strict=true`; `enforce_admins=true`; reviews adicionais desabilitados; force-push e exclusão desabilitados |
| PR de prova vermelho | [`#2`](https://github.com/Wf-ops1/Harnessinfra/pull/2), commit `d9640ff57d2e29c37f257e6a13c08025e68a69bd`; run [`30879998396`](https://github.com/Wf-ops1/Harnessinfra/actions/runs/30879998396) falhou em 4 jobs de testes e em `CI required`; `mergeable_state=blocked` |
| Restauração da prova | Revert `79af2e353ed0743082355364bb8c3a24d98c90bd`; run [`30880164178`](https://github.com/Wf-ops1/Harnessinfra/actions/runs/30880164178) com 11/11 jobs verdes e `mergeable_state=clean`; PR #2 fechado sem merge |

| Pergunta obrigatória | Resposta local F0.6 |
|---|---|
| **Qual comportamento anterior foi substituído?** | O repositório não possuía pipeline; todos os gates dependiam de execução manual. |
| **Qual é o novo contrato público?** | Um workflow versionado executará quality, unit/E2E e package/smoke em Windows/Linux; o check estável `CI required` falha se qualquer família não concluir com sucesso. |
| **Quais erros tipados podem ocorrer?** | Scripts retornam exit não zero para YAML/contrato inválido, teste/gate falho, número inesperado de wheels, bytecode no artefato, instalação/import/CLI divergente ou job dependente não sucedido. |
| **Quais side effects são produzidos?** | Somente arquivos do workflow/testes e artefatos ignorados `build/`, `dist/`, egg-info e ambientes uv isolados. |
| **Onde o estado é persistido?** | Workflow em `.github/workflows/ci.yml`, contratos em testes, evidência/checkpoints neste painel e Git local. |
| **Como a operação é retomada após crash?** | Retomar de `checkpoint/f0.6-complete`; confirmar PR #1 aberto/verde e proteção de `main` antes de qualquer promoção. |
| **Qual política autoriza a ação?** | DEC-001/002, dossiê F0.6 `READY` e `checkpoint/f0.6-ready`. |
| **Como secrets são protegidos?** | Workflow usa apenas `contents: read`, checkout sem credenciais persistidas e nenhuma secret. |
| **Quais eventos são emitidos?** | GitHub registrou check runs de quality, tests, package e `CI required` em push e pull request, com URLs preservadas acima. |
| **Quais testes provam sucesso?** | Quatro regressões do workflow, suíte 73+6, gates estáticos, build/smoke uv isolado e múltiplos runs remotos 11/11 verdes. |
| **Quais testes provam falha segura?** | Além dos contratos locais, o PR #2 comprovou `CI required=failure` e merge bloqueado; o revert comprovou restauração integral para 11/11 verdes. |
| **A wheel instalada externamente foi testada?** | Sim; uv `--isolated --no-project --with <wheel>`, com origem no cache isolado e CLI aprovada. |
| **A documentação foi atualizada?** | Sim; README, plano, auditoria, guia e este painel registram CI remota obrigatória e preservam as limitações de produto ainda reais. |

**Aceite remoto concluído:**

1. [x] publicar somente a branch `phase/f0-baseline` no `origin`;
2. [x] observar o primeiro conjunto de 4 quality, 4 tests, 2 package e o aggregate `CI required`;
3. [x] publicar a correção F0.6-R1 e comprovar novo run integralmente verde, sem reduzir matriz ou gates;
4. [x] abrir PR para `main` e configurar `CI required` como status check obrigatório;
5. [x] comprovar com PR controlado que uma falha obrigatória impede merge e que o revert restaura o verde;
6. [x] marcar F0.6 e Fase 0 como `completed` e ancorar o commit final em `checkpoint/f0.6-complete`.

---

### Gate de saída da Fase 0

```
[x] F0.0 concluída: executor, Python e estratégia Git registrados
[x] Pacote compila e instala em ambiente limpo
[x] Testes reproduzíveis por um único comando
[x] Nenhum documento declara produção
[x] Nenhum erro de sintaxe ou encoding permanece
[x] CI mínima Windows/Linux executa os gates obrigatórios e smoke da wheel
```

---

## 7. Resumo das Fases Futuras

| Fase | Objetivo resumido | Gate de saída |
|------|-------------------|---------------|
| **F1** — Contrato de grafo e compilador único | YAMLs → artefatos executáveis, validados e determinísticos | Runtime recebe apenas artefatos que passaram todas as validações |
| **F2** — Runtime real e persistência retomável | Executar cada nó; persistir transições; retomar após interrupção | E2E prova execução pela ordem das arestas compiladas, sem hardcode |
| **F3** — Modelos, ferramentas e workspace reais | Substituir simulações por providers reais; efeitos só no worktree | E2E: alteração real + commit candidato sem tocar checkout original |
| **F4** — Contexto, planejamento e verificação reais | Remover scores fabricados; contexto verificável; gates reais bloqueiam promoção | Alteração quebrada falha → corrigida em retry → promovida |
| **F5** — Governança e segurança no caminho crítico | Políticas, trust boundary, orçamento, segredos e aprovação controlam a execução | Nenhum side effect sem decisão de política registrada |
| **F6** — Observabilidade, auditoria, doctor e recovery | Operar, diagnosticar e recuperar com evidências confiáveis | Crash em checkpoint → retomada ou bloqueio sem corrupção |
| **F7** — E2E de produto, release e maturidade | Provar funcionamento fora do repositório; disciplina de release | Publicar versão `0.x` como MVP operacional |
| **F8** — Expansão de infraestrutura | Outros workflows, linguagens, isolamento forte, state alternativo, adapter MAF | Somente após F7 estável |

> Detalhes completos: headings `Fase 1` a `Fase 8` do documento principal. Não usar números de linha como referência persistente.

---

## 8. Decisões Tomadas Durante a Implementação

| Data | ID | Decisão | Motivo | Impacto |
|------|----|----------|--------|---------|
| 2026-08-03 | DEC-001 | Adotar gate obrigatório de defensabilidade antes de toda transição para `in_progress` | Impedir implementação baseada apenas em hipótese e garantir aceite e recuperação definidos antes de editar código | Toda tarefa deve comprovar problema, congelar escopo/aceite e registrar checkpoint/rollback |
| 2026-08-04 | DEC-002 | Adotar `uv`, `uv.lock` e Python `>=3.11,<3.15` como contrato do ambiente | Eliminar bootstrap ad hoc e tornar sync/test/lint/typecheck/build reproduzíveis | F0.3 cria ambiente local `.venv`; F0.6 deverá validar a faixa Python na CI |
| 2026-08-04 | DEC-003 | Versionar pacote, schemas e definições em namespaces separados | Evitar que 0.1.0, 1.0/1.0.0 e 3.2.0 sejam comparados ou atualizados como se representassem o mesmo contrato | Metadata instalada governa package version; schemas começam em 1.0; 3.2.0 permanece definition version até migrações futuras |
| 2026-08-04 | DEC-004 | Classificar claims públicos como implementados, experimentais/simulados ou planejados | Impedir que presença de classe/teste interno seja confundida com efeito operacional real | README/docs e regressão automatizada devem expor limitações e bloquear rótulos positivos sem evidência |
| 2026-08-04 | DEC-005 | Exigir `CI required` em `main`, com branch atualizada e regra aplicada a administradores | Fazer o aggregate fail-closed governar merges reais, sem bypass administrativo implícito | PR #2 comprovou estado bloqueado no vermelho e restauração para limpo após revert; PR #1 permanece aberto e verde |
| 2026-08-04 | DEC-006 | Separar capability declarada de adapter operacional e aplicar default-deny/deny-wins na resolução F1.3 | Evitar que um nome presente em YAML seja confundido com ferramenta executável ou que policy/role seja ampliada pelo node | F1.3 produz visão efetiva tipada; F1.4 integra o compilador, F3 implementa adapters e F5 impõe a decisão antes de side effects |
| 2026-08-04 | DEC-007 | Adotar `ai_engineering_harness.compiler.GraphCompiler` como único pipeline e remover injeção implícita do wrapper | Dois artefatos e GateInjector contradizem validação única e arestas explícitas F1.1 | Wrapper e CLI apenas delegam; output é `CompiledGraphArtifact`; expansão/digest ficam F1.5 e execução das policies fica F2/F5 |
| 2026-08-06 | DEC-008 | Evoluir o artifact schema de `1.0` para `2.0` e exigir compatibilidade exata, digests semânticos, proveniência e publicação atômica na F1.5 | Os campos obrigatórios são incompatíveis com o envelope F1.4 e preencher metadata ausente no load ocultaria adulteração/obsolescência | Artefato 1.0 deve ser recompilado, nunca migrado silenciosamente; capabilities continuam declarativas até F3/F5 e runtime por arestas continua F2 |
| 2026-08-06 | DEC-009 | Integrar uma tarefa por branch e PR a partir da F2.1, sempre sobre `main` pós-merge verde | PRs menores aceleram diagnóstico/revert e impedem que tarefas futuras se acumulem fora da linha oficial | `task/<id>-<descricao-curta>` nasce de `main`; um PR/merge commit por tarefa; próxima tarefa só após merge e CI pós-merge; F1 é exceção histórica promovida em um PR |

> Registre aqui toda decisão arquitetural que diverge do plano. Formato: data ISO, ID (ADR-XXX), descrição, motivo, arquivos impactados.

---

## 9. Bloqueios Atuais

| ID | Descrição | Tarefa bloqueada | Status |
|----|-----------|-----------------|--------|
| — | *Nenhum bloqueio ativo* | — | — |

### Bloqueios resolvidos

| ID | Resolução | Evidência |
|----|-----------|----------|
| B-001 | Repositório Git criado e conectado ao GitHub | `main...origin/main`, working tree limpo, remote `https://github.com/Wf-ops1/Harnessinfra.git`, HEAD `6eef8e0` |
| B-002 | Runtime Python do executor resolvido | Python `3.12.13` em `C:\Users\walla\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe` |

---

## 10. Último Checkpoint

```
Data:              2026-08-06
Fase:              F1
Tarefa:            GOV-GIT-001 — formalizar ciclo Git/execução por tarefa (DEC-009)
Estado:            completed documental — regra ativa para F2.1+; Fase 1 permanece concluída; Fase 2 não iniciada
Arquivos alterados: .agents/AGENTS.md, docs/plano_implementacao_harness_operacional.md e TASK.md; zero produto/teste/dependência
Validações:         8 testes documentais + 6 subtests; UTF-8/Markdown, regras cruzadas, git diff --check e auditoria de escopo verdes
Checkpoint:         checkpoint/f1.5-complete permanece o marco da implementação; commit documental GOV-GIT-001 subsequente na mesma branch antes do PR da F1
Observação:         phase/f1-compiler-unification publicada e sincronizada antes desta documentação; nenhum PR/merge/tag remota/proteção executado
Resultado:          uma branch + um PR por tarefa, main pós-merge verde como única base futura e exceção histórica da F1 persistidos fora do chat
```

---

## 11. Próxima Ação Exata

```text
PROMOVER A F1 SOB A DEC-009 — NÃO INICIAR IMPLEMENTAÇÃO DA F2:
1. Confirmar phase/f1-compiler-unification limpa/sincronizada, checkpoint/f1.5-complete ancestral e commit documental GOV-GIT-001 no HEAD.
2. Somente com autorização explícita, abrir um único PR da branch da F1 para main; não enviar tags nem alterar proteção.
3. Exigir branch atualizada e CI required verde; revisar que o diff contém F1.1–F1.5 e a documentação DEC-009, sem fases futuras.
4. Somente com autorização explícita adicional, usar merge commit; não usar squash, rebase, force-push ou bypass.
5. Após merge, confirmar main...origin/main, merge SHA, PR e CI pós-merge verde e registrar a promoção observada no TASK.md.
6. Criar task/f2.1-execution-record somente da main promovida; preparar apenas o dossiê/gate F2.1 antes de código.
```

---

## 12. Protocolo de Retomada após Perda de Contexto

**Todo agente que retomar esta sessão DEVE executar os passos abaixo antes de qualquer implementação.**

### Passo 1 — Ler este arquivo integralmente

Ler TASK.md do início ao fim.
Identificar: fase atual, última tarefa completed, próxima ação.

### Passo 2 — Ler a seção da fase atual no documento principal

Abrir: `docs/plano_implementacao_harness_operacional.md`
Localizar a seção da fase atual e ler todos os detalhes das tarefas pendentes.

### Passo 3 — Inspecionar estado do repositório

1. Verificar se `.git` existe.
2. Se `.git` não existir, não executar comandos Git; reabrir B-001 e solicitar decisão do usuário.
3. Se `.git` existir, executar:

   ```bash
   git status --short --branch
   git diff
   git log --oneline -10
   ```

### Passo 4 — Verificar arquivos do último checkpoint

Ler os arquivos listados em "Último Checkpoint > Arquivos alterados".
Confirmar se correspondem ao estado descrito.

### Passo 5 — Executar comandos de validação registrados

Para cada tarefa com status `completed`: re-executar seus "Comandos de verificação".
Se qualquer validação falhar: reverter status para `in_progress` e investigar antes de continuar.

### Passo 6 — Identificar a primeira tarefa não concluída

Prioridade: `in_progress` > `pending`
Nunca refazer tarefa `completed` cujas validações passaram.

### Passo 7 — Continuar pela tarefa identificada

Executar exatamente o que está em "Próxima Ação Exata".
Atualizar status neste TASK.md ao concluir cada tarefa.

---

### Regras de manutenção deste arquivo

- Atualizar status das tarefas ao concluir cada uma.
- Nunca marcar `completed` sem executar os critérios de aceite.
- Manter um único executor ativo; outros agentes devem auditar sem escrever.
- Se o executor ou ambiente mudar, reabrir F0.0 e repetir o preflight antes de editar código.
- Registrar em "Arquivos alterados" do checkpoint todos os arquivos modificados.
- Registrar em "Decisões" qualquer divergência do plano principal.
- Nunca depender apenas do histórico da conversa.
- Ao finalizar uma fase: ler a próxima fase no documento principal e substituir a seção detalhada de tarefas.
- Preservar checkpoints anteriores de forma compacta.

---

*Atualizado em: 2026-08-06 | Fonte de verdade: docs/plano_implementacao_harness_operacional.md*
