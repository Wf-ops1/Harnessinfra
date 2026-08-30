# Limitações conhecidas — 0.2.0rc1

A versão `0.2.0rc1` é a release candidate do MVP operacional. Ela comprova um caminho público
instalado e fail-closed, mas continua sendo uma prerelease `0.x`: não é `1.0`, não é uma declaração
de produção e não autoriza autonomia irrestrita sobre repositórios valiosos.

## Escopo operacional certificado

- somente o workflow `new-feature` possui composição pública integral;
- execução local em uma máquina, para projetos Python versionados com Git;
- Windows e Linux são certificados pela matriz obrigatória de CI;
- macOS possui contrato de instalação e paths documentados, mas não tem job de CI;
- a distribuição da RC ocorre por GitHub Release; não há publicação em PyPI.

## Dependências externas e integrações

- providers OpenAI/local exigem seleção, endpoint, serviço e credencial explícitos; indisponibilidade
  falha fechado;
- o adapter Anthropic não está implementado;
- Serena/MCP permanece opcional e requer configuração/serviço externos;
- o backend estrutural local é Python-only e usa rebuild integral; memória semântica externa não faz
  parte desta RC;
- `doctor` não instala, inicia nem autentica serviços: ele somente mede o ambiente configurado.

## Segurança, recovery e compatibilidade

- journal e evidence são tamper-evident locais; sem chave/âncora externa não oferecem imutabilidade
  externa nem não repúdio;
- rollback usa `git revert` e valida o novo SHA, mas não reexecuta automaticamente todos os gates
  depois da reversão;
- efeito iniciado sem outcome pode exigir intervenção humana, conforme a matriz de recovery;
- interfaces, schemas e defaults continuam prerelease e não possuem promessa de compatibilidade
  estável entre versões `0.x`;
- workflows `bug-fix`, `refactoring`, `migration` e `incident` não recebem a composição pública da
  F7.C1 nesta RC.

## Uso responsável

Comece em clone ou repositório descartável, execute `harness doctor --workflow new-feature`, revise a
configuração efetiva e mantenha aprovação humana para promoção. Credenciais, grants, trust, policy,
provider ou gate ausente não devem ser contornados: são bloqueios intencionais.

Defeitos e vulnerabilidades seguem a [política de suporte](SUPPORT.md). O estado executável e as
evidências da F7.5 ficam no [painel operacional](TASK.md).
