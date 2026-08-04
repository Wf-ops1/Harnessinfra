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

**Status da fase:** `in_progress` — F0.0 a F0.5 concluídas; F0.6 está em execução remota. O primeiro
run comprovou `EXE001` somente no Linux; a correção mínima F0.6-R1 foi congelada e validada localmente.

### Coordenação e ambiente observado

| Campo | Valor atual |
|---|---|
| **Executor ativo** | `Codex` — responsável por implementar, validar, manter checkpoints e criar commits locais |
| **Auditor/revisor** | `Antigravity` — somente-leitura por padrão; só edita quando o usuário solicitar explicitamente ou transferir a execução |
| **Workspace** | `C:\Users\walla\OneDrive\Desktop\ai-engineering-harness` |
| **Git** | `available` — `phase/f0-baseline` publicada e acompanhando `origin/phase/f0-baseline`; primeiro commit remoto validado `56b104fd1158bd3af35de28f686140b65b61c5ac`; `main` e tags não foram alteradas |
| **python_command** | `& 'C:\Users\walla\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'` — Python `3.12.13` |
| **uv_command** | `& '.\build\f0.6-tools\uv\bin\uv.exe'` — uv `0.11.32` restaurado de forma isolada/ignorada, sem PATH ou instalação global; `lock --check` e `sync --all-extras --locked` verdes |
| **Dependências do projeto** | `.venv` sincronizada pelo uv com Python 3.12.13 e `uv.lock`; 73 testes + 6 subtests, mypy em 86 arquivos, ruff, compileall, build e smoke isolado da wheel verdes |
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
| **Status** | `in_progress` — primeiro run remoto concluído com falha Linux diagnosticada; correção F0.6-R1 validada localmente; novo run e branch protection permanecem obrigatórios |
| **Objetivo** | Pipeline automatizado impede merge com falhas em encoding, lint, tipos, testes ou build |
| **Arquivos envolvidos** | `.github/workflows/*.yml` (ou equivalente CI) |
| **Implementação esperada** | Pipeline Windows + Linux com jobs: encoding/compileall; ruff; mypy; testes unitários; E2E locais; build da wheel; instalação e smoke test. Merge bloqueado quando job obrigatório falha |
| **Critérios de aceite** | Pipeline verde em Windows e Linux; PR com erro em job obrigatório é bloqueado |
| **Comandos de verificação** | Execução local (`act`) ou validação manual na CI escolhida |
| **Dependências** | F0.1, F0.2, F0.3, F0.4, F0.5 |

#### Gate de defensabilidade da F0.6

| Campo | Estado atual |
|---|---|
| **Gate** | `REMOTE_FAILED_DIAGNOSED → CORRECTION_LOCAL_VALIDATED` — `EXE001` comprovado no Ubuntu; correção mínima preparada sem alterar conteúdo Python ou reduzir gates |
| **Checkpoint de rollback** | `checkpoint/f0.5-complete` → `7cd6d81137b64914b8f53f6067f76f42cfde2711` |
| **Checkpoint de liberação** | `checkpoint/f0.6-ready` — tag criada no commit deste dossiê antes do primeiro workflow |
| **Fronteira externa** | Publicação somente de `phase/f0-baseline` autorizada e executada; `main`, tags, PR e branch protection não foram alterados; F0.6 não pode ser `completed` sem execução remota verde e proteção comprovada |

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
      main deverá exigir o check estável CI required após ele existir no GitHub; configuração remota
      não faz parte do commit local e precisa de autorização/credencial
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

| Pergunta obrigatória | Resposta local F0.6 |
|---|---|
| **Qual comportamento anterior foi substituído?** | O repositório não possuía pipeline; todos os gates dependiam de execução manual. |
| **Qual é o novo contrato público?** | Um workflow versionado executará quality, unit/E2E e package/smoke em Windows/Linux; o check estável `CI required` falha se qualquer família não concluir com sucesso. |
| **Quais erros tipados podem ocorrer?** | Scripts retornam exit não zero para YAML/contrato inválido, teste/gate falho, número inesperado de wheels, bytecode no artefato, instalação/import/CLI divergente ou job dependente não sucedido. |
| **Quais side effects são produzidos?** | Somente arquivos do workflow/testes e artefatos ignorados `build/`, `dist/`, egg-info e ambientes uv isolados. |
| **Onde o estado é persistido?** | Workflow em `.github/workflows/ci.yml`, contratos em testes, evidência/checkpoints neste painel e Git local. |
| **Como a operação é retomada após crash?** | Retomar de `checkpoint/f0.6-local-validated`; confirmar status limpo e repetir o teste do workflow antes de qualquer push. |
| **Qual política autoriza a ação?** | DEC-001/002, dossiê F0.6 `READY` e `checkpoint/f0.6-ready`. |
| **Como secrets são protegidos?** | Workflow usa apenas `contents: read`, checkout sem credenciais persistidas e nenhuma secret. |
| **Quais eventos são emitidos?** | Localmente apenas saída de ferramentas; no GitHub serão check runs de quality, tests, package e `CI required`. |
| **Quais testes provam sucesso?** | Quatro regressões do workflow, suíte 73+6, gates estáticos, build e smoke uv isolado. |
| **Quais testes provam falha segura?** | O contrato rejeita action móvel, matriz/trigger/job ausente e aggregate não fail-closed; smoke rejeita bytecode, wheel ambígua, import do checkout e versões divergentes. |
| **A wheel instalada externamente foi testada?** | Sim; uv `--isolated --no-project --with <wheel>`, com origem no cache isolado e CLI aprovada. |
| **A documentação foi atualizada?** | Sim; README informa workflow local e mantém execução remota/branch protection como pendência. |

**Aceite remoto ainda pendente — F0.6 não está concluída:**

1. [x] publicar somente a branch `phase/f0-baseline` no `origin`;
2. [x] observar o primeiro conjunto de 4 quality, 4 tests, 2 package e o aggregate `CI required`;
3. [ ] publicar a correção F0.6-R1 e comprovar novo run integralmente verde, sem reduzir matriz ou gates;
4. [ ] com nova autorização, abrir PR para `main` e configurar `CI required` como status check obrigatório;
5. [ ] comprovar com PR controlado que uma falha obrigatória impede merge;
6. [ ] somente então marcar F0.6 e Fase 0 como `completed` e criar `checkpoint/f0.6-complete`.

---

### Gate de saída da Fase 0

```
[x] F0.0 concluída: executor, Python e estratégia Git registrados
[x] Pacote compila e instala em ambiente limpo
[x] Testes reproduzíveis por um único comando
[x] Nenhum documento declara produção
[x] Nenhum erro de sintaxe ou encoding permanece
[ ] CI mínima Windows/Linux executa os gates obrigatórios e smoke da wheel
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
Data:              2026-08-04
Fase:              F0
Tarefa:            F0.6-R1 — corrigir divergência comprovada no lint Linux
Estado:            in_progress — primeiro run remoto falhou de modo seguro; correção local validada
Arquivos alterados: metadata Git de compiler/compile.py (100644 → 100755); TASK.md
Validações:         blob Python inalterado; modo staged 100755; 12 testes focados + 6 subtests; ruff; compileall; diff check — todos verdes
Checkpoint:         checkpoint/f0.6-local-validated na branch phase/f0-baseline; rollback em checkpoint/f0.6-ready e checkpoint/f0.5-complete
Observação:         branch publicada; main/tags/PR/branch protection intactos; run 30878935976 falhou somente por EXE001 no Ubuntu
Resultado:          CI provou 8 jobs verdes, 2 quality Ubuntu vermelhos e aggregate fail-closed; correção mínima pronta para commit/push
```

---

## 11. Próxima Ação Exata

```text
CONCLUIR A CORREÇÃO REMOTA F0.6-R1:
1. Confirmar no diff que compiler/compile.py muda somente de modo 100644 para 100755 e que TASK.md registra o recongelamento.
2. Criar commit da correção na phase/f0-baseline e publicar somente essa branch; não alterar main nem tags.
3. Acompanhar o novo run até os 4 quality, 4 tests, 2 package e CI required concluírem success.
4. Registrar URL, commit e resultados finais neste painel.
5. Com nova autorização, abrir PR e configurar CI required como check obrigatório de main.
6. Provar bloqueio de merge com falha controlada e depois restaurar a branch de teste.
7. Somente após todos os critérios remotos marcar F0.6/Fase 0 completed e criar checkpoint/f0.6-complete.
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

*Atualizado em: 2026-08-04 | Fonte de verdade: docs/plano_implementacao_harness_operacional.md*
