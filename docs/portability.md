# Instalação e portabilidade

> **Estado:** contrato local da F7.4; ainda não existe distribuição pública estável.

## Construir e instalar a wheel local

No clone de desenvolvimento, construa os artefatos com:

```bash
uv sync --all-extras --locked
uv run python -m build
uv run python tests/ci/smoke_wheel.py
```

O smoke seleciona a única wheel em `dist/`, instala-a com `uv` isolado e executa `harness init` em
um diretório temporário externo ao checkout. Uma wheel específica também pode ser informada como
argumento. Para validação local fora do `PATH`, defina `HARNESS_TEST_UV` com o executável exato do
`uv`.

Instalação manual da wheel construída:

```powershell
# Windows PowerShell
uv tool install .\dist\ai_engineering_harness-0.1.0-py3-none-any.whl
```

```bash
# Linux ou macOS
uv tool install ./dist/ai_engineering_harness-0.1.0-py3-none-any.whl
```

Confirme com `harness --version`. Como o pacote ainda é um protótipo, prefira um ambiente isolado e
um repositório descartável. Isso não é uma instrução para publicar a wheel em registry.

## Recursos e estado do projeto

Os templates nativos são lidos com `importlib.resources` a partir da distribuição instalada. O
comando não depende de um checkout contendo `src/ai_engineering_harness` e não sobrescreve um arquivo
já existente no scaffold.

`harness init` sempre cria o estado do projeto sob `<raiz-do-projeto>/.harness/`. Esse path é relativo
ao diretório em que o comando é executado e tem o mesmo contrato nos três sistemas. Use um diretório
cujo path canônico pertença ao repositório autorizado.

## Worktrees externos por sistema

Quando a API de worktree não recebe `external_base_dir`, o diretório base é:

| Sistema | Path padrão |
|---|---|
| Windows | `%LOCALAPPDATA%\ai-engineering-harness\worktrees\<project-id>\<execution-id>` |
| macOS | `~/Library/Application Support/ai-engineering-harness/worktrees/<project-id>/<execution-id>` |
| Linux | `~/.local/share/ai-engineering-harness/worktrees/<project-id>/<execution-id>` |

O `ExternalWorktreeManager` exige raiz Git real, checkout original limpo e identidade durável. A
remoção é explícita e recusada para worktree sujo ou divergente. O diretório pode ser substituído pela
API com `external_base_dir`; isso não amplia a trust boundary autorizada.

## Processos e matriz de suporte

O terminal executa somente `argv`, com `shell=False`. No Windows, a árvore autorizada é confinada por
Job Object; em sistemas POSIX, por grupo de processos. Timeout e cancelamento encerram a árvore
vinculada sem transformar sucesso ambíguo em êxito.

A CI obrigatória executa quality, testes e package em Windows e Linux. Os paths macOS acima seguem o
contrato implementado, mas não são certificados por job macOS na F7.4. Consulte a
[política de suporte](../SUPPORT.md) e os [quality gates](quality_gates.md) antes de relatar um defeito.

## Limite operacional atual

Instalação portável não significa autonomia operacional. Provider, tools, worktree e aprovações ainda
não são compostos automaticamente pelo caminho público; essa lacuna pertence à F7.C1, antes da
release candidate F7.5.
