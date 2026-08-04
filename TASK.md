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

## 5. Fase Atual

**→ FASE 0 — Baseline honesta, executável e reproduzível**

**Objetivo:** garantir que o pacote compile, instale, rode testes reproduzivelmente
e não anuncie capacidades inexistentes.

**Status da fase:** `blocked` — F0.0 identificou ausência de `.git`; implementação aguarda decisão explícita sobre restaurar o histórico ou criar um baseline novo.

### Coordenação e ambiente observado

| Campo | Valor atual |
|---|---|
| **Executor ativo** | `Antigravity` — responsável por implementar e atualizar checkpoints |
| **Auditor/revisor** | `Codex` — somente-leitura por padrão; só edita quando o usuário solicitar explicitamente |
| **Workspace** | `C:\Users\walla\OneDrive\Desktop\ai-engineering-harness` |
| **Git** | `initialized` — conectado e sincronizado com `https://github.com/Wf-ops1/Harnessinfra.git` (branch `main`) |
| **python_command** | `unresolved` — `python` e `py` não estavam disponíveis no shell da auditoria; o executor deve repetir o preflight |
| **Regra de escrita** | apenas um agente escreve por vez |

---

## 6. Tarefas da Fase Atual

---

### F0.0 — Preflight do workspace e coordenação dos agentes

| Campo | Detalhe |
|-------|---------|
| **Status** | `blocked` |
| **Objetivo** | Definir um executor único e comprovar Python/Git disponíveis antes de qualquer alteração de código |
| **Arquivos envolvidos** | `TASK.md`, `.agents/AGENTS.md`; nenhuma alteração de código nesta tarefa |
| **Implementação esperada** | (1) escolher um único executor; (2) detectar `uv`, `python` e `py`; (3) registrar `python_command` com versão `>=3.11`; (4) verificar Git somente se `.git` existir; (5) se `.git` estiver ausente, solicitar decisão para restaurar histórico ou criar baseline; (6) não executar `git init` nem instalar runtime sem autorização |
| **Critérios de aceite** | executor identificado; `python_command` válido ou bloqueio registrado; estado Git registrado; checkpoint e próxima ação atualizados |
| **Comandos de verificação** | PowerShell: `Get-Command uv, python, py, git -ErrorAction SilentlyContinue`; filesystem: `Test-Path -LiteralPath .git`; executar `git rev-parse --is-inside-work-tree` apenas se o teste anterior retornar `True` |
| **Dependências** | decisão do usuário sobre o Git quando `.git` estiver ausente |

> Convenção: após o preflight, substituir `<PYTHON_CMD>` pelo comando efetivamente registrado, por exemplo `uv run python`, `python` ou `py -3`. Nunca assumir um deles sem detecção.

---

### F0.1 — Corrigir erros bloqueantes de código

| Campo | Detalhe |
|-------|---------|
| **Status** | `pending` |
| **Objetivo** | Eliminar erros de sintaxe, imports quebrados e assinaturas inválidas que impedem importação do pacote |
| **Arquivos envolvidos** | `src/ai_engineering_harness/migrations/runner.py`, todos os módulos públicos do pacote |
| **Implementação esperada** | (1) Corrigir assinatura inválida em `migrations/runner.py`; (2) executar `compileall` em `src/`, `compiler/`, `tests/`; (3) corrigir imports quebrados; (4) adicionar teste que importe todos os módulos públicos |
| **Critérios de aceite** | `<PYTHON_CMD> -m compileall -q src compiler tests` exit 0; `<PYTHON_CMD> -c "import ai_engineering_harness.migrations"` exit 0 |
| **Comandos de verificação** | `<PYTHON_CMD> -m compileall -q src compiler tests`; depois `<PYTHON_CMD> -c "import ai_engineering_harness.migrations"` |
| **Dependências** | F0.0 concluída |

---

### F0.2 — Padronizar encoding

| Campo | Detalhe |
|-------|---------|
| **Status** | `pending` |
| **Objetivo** | Eliminar mojibake UTF-8 em todos os arquivos do projeto |
| **Arquivos envolvidos** | Todos os `.py`, `.md`, `.yaml`, `.toml`, `.json`; novo `.editorconfig` |
| **Implementação esperada** | (1) Converter todos os arquivos para UTF-8 válido; (2) corrigir strings corrompidas (`AutÃ´nomo`, `âœ"`, `Ã­ndice`); (3) remover lógica baseada em símbolos corrompidos; (4) criar `.editorconfig` com `charset = utf-8`; (5) validar CLI em Windows UTF-8 e console legado |
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
| **Comandos de verificação** | `uv sync --all-extras && uv run python -m pytest && uv run python -m mypy src && uv run python -m ruff check . && uv run python -m build` |
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
| **Comandos de verificação** | `harness --version` e `<PYTHON_CMD> -c "import ai_engineering_harness; print(ai_engineering_harness.__version__)"` |
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
[ ] F0.0 concluída: executor, Python e estratégia Git registrados
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
| — | — | *Nenhuma decisão registrada ainda* | — | — |

> Registre aqui toda decisão arquitetural que diverge do plano. Formato: data ISO, ID (ADR-XXX), descrição, motivo, arquivos impactados.

---

## 9. Bloqueios Atuais

| ID | Descrição | Tarefa bloqueada | Status |
|----|-----------|-----------------|--------|
| B-001 | `.git` não existe no workspace; não há diff, histórico ou rollback confiável | F0.0 e toda implementação subsequente | aguardando decisão do usuário: restaurar histórico ou autorizar baseline novo |
| B-002 | Comando Python do executor ainda não foi resolvido; `python` e `py` não estavam disponíveis no shell da auditoria | F0.0 | executor deve repetir detecção e registrar `<PYTHON_CMD>` |

---

## 10. Último Checkpoint

```
Data:              2026-08-03
Fase:              F0
Tarefa:            F0.0
Estado:            blocked
Arquivos alterados: TASK.md, docs/plano_implementacao_harness_operacional.md, .agents/AGENTS.md
Validações:         executor Antigravity definido; `.git` ausente; `python_command` não resolvido no shell da auditoria
Resultado:          implementação não deve começar até resolver B-001 e B-002
```

---

## 11. Próxima Ação Exata

```text
CONCLUIR F0.0:
1. Antigravity, como executor ativo, repete a detecção de `uv`, `python`, `py` e registra `<PYTHON_CMD>`.
2. Codex permanece como auditor somente-leitura, salvo pedido explícito do usuário.
3. O usuário decide como recuperar versionamento: restaurar `.git` original é preferível; criar baseline novo exige autorização explícita.
4. O executor confirma o estado Git sem executar `git init` automaticamente.
5. Atualizar F0.0 e os bloqueios B-001/B-002.
6. Somente após F0.0 ficar `completed`, iniciar F0.1.
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
2. Se `.git` não existir, não executar comandos Git; manter B-001 e solicitar decisão do usuário.
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
- Registrar em "Arquivos alterados" do checkpoint todos os arquivos modificados.
- Registrar em "Decisões" qualquer divergência do plano principal.
- Nunca depender apenas do histórico da conversa.
- Ao finalizar uma fase: ler a próxima fase no documento principal e substituir a seção detalhada de tarefas.
- Preservar checkpoints anteriores de forma compacta.

---

*Gerado em: 2026-08-03 | Fonte de verdade: docs/plano_implementacao_harness_operacional.md*
