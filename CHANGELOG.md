# Changelog

Todas as mudanças relevantes deste projeto serão registradas neste arquivo. O formato segue
[Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o projeto usa versionamento semântico
para suas releases públicas prerelease.

## [Não publicado]

## [0.2.0rc1] — 2026-08-30 — MVP operacional release candidate

### Adicionado

- composição pública canônica do workflow `new-feature`, com falha fechada para autoridade ou
  integração ausente;
- E2E da wheel instalada em repositório Git externo, cobrindo provider de produção contra transporte
  controlado, tools, worktree, gates, aprovação, promoção, evidence e rollback;
- quality gates obrigatórios de mypy strict, cobertura decisória, secrets e dependências;
- carregamento dos defaults instalados por `importlib.resources`;
- smoke da wheel em diretório externo ao checkout;
- documentação de licença, suporte e portabilidade Windows, macOS e Linux.
- lista pública de [limitações conhecidas](KNOWN_LIMITATIONS.md).

### Limitações

- prerelease `0.x`, não `1.0` nem declaração de produção;
- somente `new-feature` possui composição pública integral;
- distribuição por GitHub Release, sem publicação em PyPI;
- consulte [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) antes de usar.

## [0.1.0] — protótipo em desenvolvimento

- baseline inicial do AI Engineering Harness; não corresponde a uma release pública estável.

[Não publicado]: https://github.com/Wf-ops1/Hartrol/compare/v0.2.0-rc.1...HEAD
[0.2.0rc1]: https://github.com/Wf-ops1/Hartrol/releases/tag/v0.2.0-rc.1
[0.1.0]: https://github.com/Wf-ops1/Hartrol/tree/main
