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

---

## 5. Fase Atual

**→ FASE 0 — Baseline honesta, executável e reproduzível**

**Objetivo:** garantir que o pacote compile, instale, rode testes reproduzivelmente
e não anuncie capacidades inexistentes.

**Status da fase:** `in_progress` — F0.0 e F0.1 concluídas; próxima tarefa: F0.2, que permanece
`pending` até seu próprio gate de defensabilidade ser comprovado e marcado como `READY`.

### Coordenação e ambiente observado

| Campo | Valor atual |
|---|---|
| **Executor ativo** | `Codex` — responsável por implementar, validar, manter checkpoints e criar commits locais |
| **Auditor/revisor** | `Antigravity` — somente-leitura por padrão; só edita quando o usuário solicitar explicitamente ou transferir a execução |
| **Workspace** | `C:\Users\walla\OneDrive\Desktop\ai-engineering-harness` |
| **Git** | `available` — branch de execução `phase/f0-baseline`, criada a partir de `main`/`origin/main` no baseline `6eef8e0`; remote `https://github.com/Wf-ops1/Harnessinfra.git` |
| **python_command** | `& 'C:\Users\walla\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'` — Python `3.12.13` |
| **Dependências do projeto** | runtime suficiente para F0.1; `yaml`, `click`, `rich`, `httpx` e `pytest` ainda não estão disponíveis neste runtime e serão tratadas na F0.3 |
| **Regra de escrita** | apenas um agente escreve por vez |

---

## 6. Tarefas da Fase Atual

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
| **Status** | `pending` |
| **Objetivo** | Eliminar mojibake UTF-8 em todos os arquivos do projeto |
| **Arquivos envolvidos** | Todos os `.py`, `.md`, `.yaml`, `.toml`, `.json`; novo `.editorconfig` |
| **Implementação esperada** | (1) Converter todos os arquivos para UTF-8 válido; (2) corrigir strings corrompidas (`AutÃ´nomo`, `âœ”`, `Ã­ndice`); (3) remover lógica baseada em símbolos corrompidos; (4) criar `.editorconfig` com `charset = utf-8`; (5) validar CLI em Windows UTF-8 e console legado |
| **Critérios de aceite** | `rg` sem mojibake conhecido em src/docs/README; `harness --help` e `harness doctor` sem exceção |
| **Comandos de verificação** | `rg -n 'Ã|âœ|ðŸ' src docs README.md` → sem resultados |
| **Dependências** | F0.1 |

---

### F0.3 — Tornar o ambiente reproduzível

| Campo | Detalhe |
|-------|---------|
| **Status** | `pending` |
| **Objetivo** | Qualquer máquina limpa consegue instalar, testar e construir o pacote com um único conjunto de comandos |
| **Arquivos envolvidos** | `pyproject.toml`, `uv.lock`, `README.md` |
| **Implementação esperada** | (1) Adotar `uv` como gerenciador de ambiente; (2) criar e versionar `uv.lock`; (3) completar deps dev: pytest, pytest-cov, mypy, ruff, build; (4) usar `python -m ...` nos comandos internos; (5) definir versões Python suportadas; (6) documentar bootstrap no README |
| **Critérios de aceite** | Em máquina limpa: `uv sync --all-extras` OK; `uv run python -m pytest` OK; `uv run python -m mypy src` OK; `uv run python -m ruff check .` OK; `uv run python -m build` OK |
| **Comandos de verificação** | Executar separadamente: `uv sync --all-extras`; `uv run python -m pytest`; `uv run python -m mypy src`; `uv run python -m ruff check .`; `uv run python -m build` |
| **Dependências** | F0.1, F0.2 |

---

### F0.4 — Unificar versionamento

| Campo | Detalhe |
|-------|---------|
| **Status** | `pending` |
| **Objetivo** | Uma única fonte de versão do pacote; schemas versionados separadamente |
| **Arquivos envolvidos** | `pyproject.toml`, `src/ai_engineering_harness/__init__.py`, schemas de grafo/artifact/policy |
| **Implementação esperada** | (1) `__version__` via `importlib.metadata.version`; (2) separar `package_version`, `graph_schema_version`, `artifact_schema_version`, `policy_schema_version`; (3) remover versões conflitantes (`0.1.0`, `1.0.0`, `3.2.0`) usadas para a mesma coisa |
| **Critérios de aceite** | `harness --version`, metadata da wheel e `ai_engineering_harness.__version__` são idênticos; schemas com compatibilidade testada separadamente |
| **Comandos de verificação** | `harness --version` e o `python_command` registrado com `-c "import ai_engineering_harness; print(ai_engineering_harness.__version__)"` |
| **Dependências** | F0.1, F0.3 |

---

### F0.5 — Corrigir documentação de estado

| Campo | Detalhe |
|-------|---------|
| **Status** | `pending` |
| **Objetivo** | Documentação não deve declarar capacidades inexistentes nem conter links quebrados |
| **Arquivos envolvidos** | `README.md`, `docs/*.md` |
| **Implementação esperada** | (1) Substituir "Em Produção" por "Protótipo / Em desenvolvimento"; (2) remover referências a arquivos inexistentes; (3) corrigir links `file:///` absolutos; (4) criar matriz Capacidade/Implementada/Experimental/Planejada; (5) marcar adapters fake como dívida técnica |
| **Critérios de aceite** | Nenhum documento declara produção; nenhum link aponta para arquivo inexistente |
| **Comandos de verificação** | `rg "Em Produção" docs README.md` → sem resultados |
| **Dependências** | F0.1 |

---

### F0.6 — Criar CI mínima

| Campo | Detalhe |
|-------|---------|
| **Status** | `pending` |
| **Objetivo** | Pipeline automatizado impede merge com falhas em encoding, lint, tipos, testes ou build |
| **Arquivos envolvidos** | `.github/workflows/*.yml` (ou equivalente CI) |
| **Implementação esperada** | Pipeline Windows + Linux com jobs: encoding/compileall; ruff; mypy; testes unitários; E2E locais; build da wheel; instalação e smoke test. Merge bloqueado quando job obrigatório falha |
| **Critérios de aceite** | Pipeline verde em Windows e Linux; PR com erro em job obrigatório é bloqueado |
| **Comandos de verificação** | Execução local (`act`) ou validação manual na CI escolhida |
| **Dependências** | F0.1, F0.2, F0.3, F0.4, F0.5 |

---

### Gate de saída da Fase 0

```
[x] F0.0 concluída: executor, Python e estratégia Git registrados
[ ] Pacote compila e instala em ambiente limpo
[ ] Testes reproduzíveis por um único comando
[ ] Nenhum documento declara produção
[ ] Nenhum erro de sintaxe ou encoding permanece
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
Data:              2026-08-03
Fase:              F0
Tarefa:            F0.1 — corrigir erros bloqueantes de código
Estado:            completed
Arquivos alterados: src/ai_engineering_harness/migrations/runner.py; tests/unit/test_public_module_imports.py; TASK.md
Validações:         compileall exit 0; import migrations exit 0; unittest importou 85 módulos públicos, zero falhas/skips; git diff --check
Checkpoint:         checkpoint/f0.1-complete na branch phase/f0-baseline; rollback em checkpoint/f0.1-ready
Observação:         dependências declaradas foram usadas somente em C:/tmp; nenhum ambiente global ou manifesto foi alterado
Resultado:          erro sintático removido; pacote e testes compilam; todos os módulos públicos são importáveis no ambiente declarado
```

---

## 11. Próxima Ação Exata

```text
PREPARAR O GATE DE DEFENSABILIDADE DA F0.2 — AINDA NÃO ALTERAR ENCODING:
1. Confirmar `checkpoint/f0.1-complete`, branch, HEAD e working tree limpo.
2. Reproduzir a busca baseline de mojibake em `src`, `docs` e `README.md`, registrando arquivos e ocorrências.
3. Inspecionar `.editorconfig`, comportamento atual da CLI e qualquer lógica dependente de símbolos corrompidos.
4. Preencher o dossiê da F0.2 com problema comprovado, escopo permitido/excluído, aceite e rollback.
5. Manter F0.2 `pending` se qualquer item do gate estiver incompleto.
6. Somente depois do gate `READY`, mudar F0.2 para `in_progress` e iniciar alterações de encoding.
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

*Gerado em: 2026-08-03 | Fonte de verdade: docs/plano_implementacao_harness_operacional.md*
