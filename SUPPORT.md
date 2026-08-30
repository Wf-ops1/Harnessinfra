# Política de suporte

O AI Engineering Harness `0.2.0rc1` é a release candidate do MVP operacional. Continua sendo uma
prerelease `0.x`, sem garantia de estabilidade ou aptidão para produção. Comece em repositórios
descartáveis e leia as [limitações conhecidas](KNOWN_LIMITATIONS.md).

## Ambientes cobertos

- Python 3.11 a 3.14;
- Windows e Linux certificados pela matriz obrigatória de CI;
- macOS com paths e contrato de instalação documentados, mas ainda sem certificação de CI.

Correções são direcionadas à branch `main`. Não há, nesta fase, janela de manutenção para versões
anteriores nem garantia de compatibilidade entre interfaces prerelease.

## Solicitar ajuda

Antes de abrir uma issue, execute os comandos de diagnóstico e qualidade descritos no
[guia de portabilidade](docs/portability.md) e remova tokens, secrets, paths pessoais e conteúdo
privado dos logs. Para defeitos reproduzíveis, abra uma
[issue no repositório](https://github.com/Wf-ops1/Hartrol/issues) com sistema operacional, versão do
Python, versão do pacote, comando, resultado esperado e saída redigida.

Vulnerabilidades não devem ser divulgadas em issue pública. Use um canal privado de segurança
disponibilizado pelo mantenedor no GitHub; se ele não estiver disponível, contate primeiro o dono do
repositório sem incluir detalhes exploráveis.
