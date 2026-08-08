# AI Engineering Harness

> **Status atual: Protótipo / Em desenvolvimento**

O AI Engineering Harness é hoje uma base Python instalável para experimentar um harness de engenharia
agentic local-first. O repositório já possui empacotamento reproduzível, compilador único e
determinístico, execução dirigida pelas arestas do artefato, persistência concorrente, FSM por eventos
e retomada canônica com aprovação, cancelamento e retry limitado por contexto real e redigido. A
execução autônoma segura sobre um repositório externo ainda não está pronta: roteamento de modelos,
ferramentas, isolamento Git, promoção, rollback e governança operacional permanecem incompletos ou simulados.

Não use `harness run`, `harness doctor` ou `harness rollback` como garantia de segurança em um
repositório valioso. Embora a Fase 2 esteja implementada, as Fases 3–7 ainda não estão concluídas;
execute esses comandos somente em cópias descartáveis.

## Objetivo do produto

A arquitetura-alvo continua sendo:

\[
\text{Harness} =
\text{BMAD} \longrightarrow
\text{Graph Engineering} \longrightarrow
\text{Runtime Agentic} \longrightarrow
\text{Tools/Memory} \longrightarrow
\text{Quality/Ops}
\]

Quando concluído, o pacote deverá permitir instalar uma CLI ou integração de IDE, inicializar um
repositório externo, executar alterações dentro de um worktree isolado, bloquear efeitos não
autorizados, verificar o resultado, exigir aprovação, promover por Git e reverter com evidência
auditável. Isso é a direção do produto, não uma descrição do estado entregue.

## Matriz de capacidade

| Capacidade | Implementada | Experimental | Planejada |
|---|---|---|---|
| Ambiente e pacote | `uv.lock`, build de wheel, metadata e toolchain reproduzível | Bootstrap ainda depende de instalar `uv` | Distribuição e instalação externa suportadas como produto |
| Versionamento | Package version única e schemas graph/artifact/policy separados | Compatibilidade ainda é comparação exata | Migrações compatíveis e política de evolução |
| CLI e scaffold | `--help`, `--version`, `init`, `compile`, `run`, `resume`, `approve`, `cancel`, `status` e `inspect` possuem contratos e testes | Sem backends reais, `run` falha no preflight; doctor, audit, verify e rollback ainda cobrem componentes incompletos | UX estável para CLI e IDE em repositórios externos |
| Compilação de grafos | Um único `GraphCompiler` valida contratos/policies e publica artefato 2.0 determinístico, versionado, íntegro e atômico | Capabilities compiladas ainda são declarativas, sem provar adapter disponível ou autorização runtime | Migrações de schema e expansão segura de workflows após o MVP |
| Runtime/FSM | `GraphExecutor` segue somente arestas compiladas; record/journal usam lock, CAS e fencing; FSM event-sourced e lifecycle retomável suportam aprovação, cancelamento e retry com evidência redigida, limite e resume por digest | Efeito interrompido sem outcome exige intervenção; executores dependem de backends injetados ainda indisponíveis no produto | Efeitos reais e repair loop completo integrados nas Fases 3–6 |
| Providers LLM | OpenAI Responses API e endpoint local Chat Completions executam HTTP real, com timeout/cancelamento, retry transitório, erros/usage/tool calls tipados e structured output validado | Integração live é opt-in; Anthropic falha como não implementado; registry/router ainda não usam configuração efetiva, budget ou node events | Roteamento, fallback autorizado, budget e persistência operacional em F3.2 |
| Serena e Codebase-Memory | Interfaces/adapters existem | Serena apenas cria/toca arquivo; memória retorna `mock_ast` | Transporte MCP real ou adapter local explicitamente configurado |
| Verificação e auditoria | Subprocessos de gates e hash chain local possuem testes | Há caminhos de gate vazio e garantias ainda incompletas | Gates fail-closed, redaction e recovery operacional |
| Doctor | Relatório e modelo de probe existem | Todos os seis estágios retornam saudáveis sem testar componentes | Probes reais de configuração, alcance, autenticação e capacidade |
| Worktree, promoção e rollback | Estruturas e comandos prototípicos existem | Worktree é diretório comum; promoção usa dry-run/SHA sintético; rollback é parcial | `git worktree`, candidate commit, cherry-pick e `git revert` reais |
| CI e release | GitHub Actions executa quality/tests/package em Windows e Linux; `main` exige `CI required`, com bloqueio e restauração comprovados | A CI prova o baseline técnico, não as capacidades operacionais ainda simuladas | Distribuição pública e processo de release operacional na F7 |

## Estado do roadmap

- **Fase 0 concluída:** ambiente reproduzível, documentação honesta e CI protegida.
- **Fase 1 concluída:** contrato de grafo, registries seguros, compilador único e artefato 2.0
  determinístico.
- **Fase 2 concluída:** record atômico, storage concorrente, execução por grafo, FSM por eventos,
  retomada vinculada ao artefato/configuração originais e retry que consome erro, tool call,
  stdout/stderr redigidos, gates, diff, orçamento e instrução de correção.
- **Fase 3 em andamento:** F3.1 entrega providers remoto/local reais e falha explícita para Anthropic;
  F3.2–F3.8 ainda cobrem roteamento, tools, terminal seguro, worktree, promoção e edição.

## Dívidas técnicas críticas

As seguintes implementações são deliberadamente tratadas como dívida técnica, não como capacidades
operacionais:

- [adapters de modelos](src/ai_engineering_harness/models/adapters/) OpenAI/local já usam transporte
  real e Anthropic falha explicitamente; o [roteamento de modelos](src/ai_engineering_harness/models/router.py)
  ainda usa registry estático, não conecta usage ao budget nem persiste provider/modelo nos node events;
- [SerenaAdapter](src/ai_engineering_harness/tools/adapters/serena.py) não abre conexão MCP nem aplica
  edição semântica;
- [CodebaseMemoryAdapter](src/ai_engineering_harness/indexer/codebase_memory_adapter.py) persiste uma
  AST simulada;
- [HealthProbe](src/ai_engineering_harness/doctor/probes.py) declara todos os estágios saudáveis sem
  executar probes;
- [PromotionManager](src/ai_engineering_harness/runtime/promotion_manager.py) produz SHA sintético em
  dry-run e possui fallback sintético no caminho live;
- [ExternalWorktreeManager](src/ai_engineering_harness/workspace/git_worktree.py) cria diretório, não
  um worktree Git;
- [TerminalAdapter](src/ai_engineering_harness/tools/adapters/terminal.py) recebe string e usa
  `shell=True`, contrário ao contrato final de segurança.

## Ambiente de desenvolvimento

Pré-requisitos:

- Python 3.11, 3.12, 3.13 ou 3.14;
- `uv`;
- Git.

Após clonar:

```bash
uv sync --all-extras
uv lock --check
uv run python -m pytest
uv run python -m mypy src
uv run python -m ruff check .
uv run python -m compileall -q src compiler tests
uv run python -m build
uv run python tests/ci/smoke_wheel.py
```

Para inspecionar a superfície da CLI sem executar o runtime:

```bash
uv run harness --version
uv run harness --help
```

`harness init` escreve uma pasta `.harness/` no diretório atual. Enquanto o produto estiver em
desenvolvimento, teste o scaffold apenas em um repositório descartável.

## Contrato de versionamento

A versão autoral do pacote fica em `pyproject.toml`. Em runtime,
`ai_engineering_harness.__version__` e `harness --version` leem a metadata instalada.
`graph_schema_version`, `artifact_schema_version` e `policy_schema_version` evoluem de forma
independente; `definition_version` identifica apenas a revisão de uma definição.

## Fonte de verdade

- [TASK.md](TASK.md): painel de execução, evidências, gates e próxima ação;
- [Plano operacional](docs/plano_implementacao_harness_operacional.md): implementação necessária até
  o MVP operacional;
- [Modelo operacional](docs/agentic_operating_model.md): fluxo atual versus fluxo-alvo;
- [Auditoria do ciclo](docs/agentic_lifecycle_audit.md): estado concreto de cada etapa;
- [Especificação arquitetural](docs/harness_architecture_spec.md): arquitetura-alvo e lacunas;
- [Guia do usuário](docs/user_guide.md): comandos seguros e limitações atuais;
- [Walkthrough](docs/walkthrough.md): estrutura real e fluxo observado;
- [Auditoria técnica](docs/walkthrough_audit.md): pendências comprovadas.
