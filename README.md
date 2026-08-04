# AI Engineering Harness

> **Status atual: Protótipo / Em desenvolvimento**

O AI Engineering Harness é hoje uma base Python instalável para experimentar um harness de engenharia
agentic local-first. O repositório já possui empacotamento reproduzível, CLI, contratos, compiladores,
FSM, verificadores, auditoria e testes. A execução autônoma segura sobre um repositório externo ainda
não está pronta: integrações de modelo e MCP são simuladas, o isolamento Git não cria um worktree real
e promoção/rollback não cumprem ainda o contrato operacional do produto.

Não use `harness run`, `harness doctor` ou `harness rollback` como garantia de segurança em um
repositório valioso. Até os gates F1-F7 serem concluídos, execute esses comandos somente em cópias
descartáveis.

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
| CLI e scaffold | `--help`, `--version` e `init` existem e têm testes | Demais comandos exercitam componentes do protótipo | UX estável para CLI e IDE em repositórios externos |
| Compilação de grafos | Contratos e validadores existem | Há dois caminhos de compilação e o runtime não é governado integralmente pelas arestas | Compilador único, determinístico e fail-closed na F1 |
| Runtime/FSM | Estados, contexto, plano, evidência e diário local existem | O fluxo é orquestrado por sequência fixa e pode concluir com efeitos simulados | Execução persistida e retomável dirigida pelo artefato na F2 |
| Providers LLM | Interfaces, registry e router existem | OpenAI, Anthropic e local fabricam respostas; não fazem chamadas reais | Providers remoto e local reais, com erros tipados, na F3 |
| Serena e Codebase-Memory | Interfaces/adapters existem | Serena apenas cria/toca arquivo; memória retorna `mock_ast` | Transporte MCP real ou adapter local explicitamente configurado |
| Verificação e auditoria | Subprocessos de gates e hash chain local possuem testes | Há caminhos de gate vazio e garantias ainda incompletas | Gates fail-closed, redaction e recovery operacional |
| Doctor | Relatório e modelo de probe existem | Todos os seis estágios retornam saudáveis sem testar componentes | Probes reais de configuração, alcance, autenticação e capacidade |
| Worktree, promoção e rollback | Estruturas e comandos prototípicos existem | Worktree é diretório comum; promoção usa dry-run/SHA sintético; rollback é parcial | `git worktree`, candidate commit, cherry-pick e `git revert` reais |
| CI e release | Workflow e contrato local cobrem quality/tests/package em Windows e Linux | Execução remota e branch protection ainda precisam ser comprovadas | Check obrigatório após ativação da F0.6; release operacional na F7 |

## Dívidas técnicas críticas

As seguintes implementações são deliberadamente tratadas como dívida técnica, não como capacidades
operacionais:

- [adapters de modelos](src/ai_engineering_harness/models/adapters/) retornam conteúdo e contagens de
  tokens fabricados;
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
