# Guia de Uso do Protótipo — AI Engineering Harness

> **Status: uso de desenvolvimento em ambiente descartável**

O pacote ainda não está publicado como ferramenta operacional nem é seguro para automatizar mudanças
em um repositório valioso. Este guia descreve como inspecionar e testar o protótipo no clone do
projeto.

## Preparar o ambiente

```bash
uv sync --all-extras
uv lock --check
uv run harness --version
uv run harness --help
```

Para validar o baseline:

```bash
uv run python -m pytest
uv run python -m mypy src
uv run python -m ruff check .
uv run python -m compileall -q src compiler tests
uv run python -m build
```

## Comandos e limitações

| Comando | O que faz hoje | Estado/limitação |
|---|---|---|
| `harness --version` | Lê a versão da metadata instalada | Implementado |
| `harness init` | Cria `.harness/` e copia defaults disponíveis | Implementado como scaffold; testar somente em repo descartável |
| `harness doctor` | Renderiza quatro componentes em seis estágios | Simulado: retorna saudável sem conectividade real |
| `harness compile <yaml>` | Compila pelo `GraphCompiler` do pacote | Experimental: contratos ainda serão unificados na F1 |
| `harness index` | Persiste snapshot ligado ao texto `HEAD` | Simulado: AST é fabricada |
| `harness run <workflow>` | Executa a sequência do runtime e grava estado/evidência | Experimental: modelos, edição, memória e promoção são simulados |
| `harness status <id>` | Lê `workflow-state.json` | Experimental, restrito ao armazenamento local atual |
| `harness inspect <id>` | Exibe estado, hash chain e aprovação | Experimental |
| `harness approve <id>` | Persiste decisão de aprovação | Não retoma/promove a execução pelo protocolo final |
| `harness verify` | Executa gates Python selecionados | Experimental: cobertura e política fail-closed ainda incompletas |
| `harness audit <id>` | Verifica/exporta o diário local | Implementação local; não prova efeitos reais |
| `harness rollback <id>` | Registra compensação e pode chamar `git revert` | Não usar em repo valioso; worktree e segurança Git ainda faltam |

## Teste controlado de `init`

Crie um repositório descartável e execute o binário instalado pelo ambiente do clone. Confirme os
arquivos gerados antes de removê-los. Não aponte o protótipo para um checkout com trabalho não
commitado.

## O que ainda não está disponível

- instalação pública estável por `pipx`, `uv tool` ou extensão de IDE;
- provider LLM real;
- Serena/Codebase-Memory reais;
- edição confinada a worktree Git;
- promoção por candidate commit e cherry-pick;
- retomada após aprovação/crash;
- rollback seguro e gates pós-reversão;
- doctor confiável.

Acompanhe a ordem de implementação no
[plano operacional](plano_implementacao_harness_operacional.md) e o estado executável no
[TASK.md](../TASK.md).
