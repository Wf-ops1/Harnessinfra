# AI-Engineering-Harness — Regras Operacionais dos Agentes

## Estado atual

Este projeto ainda é um protótipo arquitetural em evolução para um harness operacional. A fórmula
`BMAD → Graph Engineering → MAF → Serena + Codebase-Memory → Quality/Ops` representa a arquitetura desejada, não uma lista de integrações já funcionais.

## Fontes de verdade

Antes de qualquer ação, ler integralmente:

1. `TASK.md` — estado atual, bloqueios, executor e próxima ação.
2. A fase ativa em `docs/plano_implementacao_harness_operacional.md` — requisitos completos e critérios de aceite.

Em caso de conflito, o pedido explícito do usuário prevalece; depois, o plano principal; por fim, o checkpoint em `TASK.md` deve ser atualizado para refletir a decisão.

## Coordenação obrigatória

1. Apenas um agente pode ser executor/escritor por vez.
2. Se outro agente estiver registrado como executor ativo em `TASK.md`, atuar somente em auditoria e não editar arquivos.
3. Antes de editar código, concluir F0.0 e registrar `python_command`, estado Git e workspace.
4. Atualizar `TASK.md` após cada tarefa, incluindo arquivos alterados, validações, decisões, bloqueios e próxima ação.
5. Nunca depender apenas do histórico da conversa para retomar trabalho.

## Git e recuperação

1. Verificar a existência de `.git` antes de executar `git status`, `git diff`, `git log` ou qualquer operação Git.
2. Se `.git` estiver ausente, não executar `git init` automaticamente. Registrar bloqueio e pedir decisão explícita ao usuário.
3. Quando Git estiver disponível, preservar mudanças existentes e criar checkpoints por tarefa.
4. Nunca apagar, resetar ou sobrescrever trabalho de outro agente para resolver conflito.
5. A partir da F2.1, criar uma branch `task/<id>-<descricao-curta>` para cada tarefa, sempre a partir
   de `main` sincronizada, com a tarefa anterior já incorporada e CI pós-merge verde.
6. Nunca desenvolver diretamente em `main` nem iniciar a tarefa seguinte sobre branch ainda não
   incorporada. Uma branch pode conter vários commits da mesma tarefa, mas não acumular tarefas futuras.
7. Cada tarefa concluída deve ter um único PR para `main`, branch atualizada e `CI required=success`.
   Preferir merge commit para preservar histórico e permitir revert isolado da tarefa.
8. Push, abertura de PR, merge, exclusão de branch/tag remota, force-push, bypass ou mudança de
   proteção exigem autorização explícita do usuário. Force-push e bypass não são o fluxo normal.
9. Antes do primeiro arquivo da tarefa seguinte, comprovar no Git/GitHub o merge anterior e o CI
   verde da `main`, registrando PR, merge SHA e run no novo checkpoint de `TASK.md`.
10. Mudanças documentais transversais usam `docs/<descricao-curta>` e PR próprio; documentos que
    preparam ou fecham uma tarefa permanecem na branch dessa tarefa.

O ciclo completo e suas exceções estão em `docs/plano_implementacao_harness_operacional.md`, seção
`Ciclo Git obrigatório por tarefa`. A F1 é a exceção histórica já concluída em uma branch linear;
o commit que adota esta regra acompanha a branch da F1 antes de seu PR. Nenhuma implementação da F2
começa antes dessa promoção para `main` e do CI pós-merge verde.

## Ambiente de execução

1. Não assumir que `python`, `py` ou `uv` existem.
2. Detectar o ambiente, selecionar Python `>=3.11` e registrar o comando como `python_command` no `TASK.md`.
3. Usar o comando registrado nos critérios de aceite; não trocar de runtime silenciosamente.
4. Instalação de runtime, dependências globais ou ferramentas requer autorização quando alterar o ambiente do usuário.

## Layout real durante a transição

- Código do pacote: `src/ai_engineering_harness/`.
- Grafos distribuídos: `src/ai_engineering_harness/defaults/graphs/`.
- Políticas distribuídas: `src/ai_engineering_harness/defaults/policies/`.
- Contratos: `src/ai_engineering_harness/contracts/`.
- Configuração copiada para projetos-alvo: `.harness/`.
- Compilador oficial: `src/ai_engineering_harness/compiler/`, concluído na Fase 1.

`compiler/compile.py` é somente um wrapper de compatibilidade que delega ao package. Paths de raiz
como `graphs/specs/`, `contracts/` e `policies/` continuam legados/inconsistentes e não são fonte de
verdade.

## Implementação e verificação

1. Não criar mocks ou respostas simuladas em código de produção.
2. Não declarar Serena, Codebase-Memory, MAF, provider, doctor, gate, promoção ou rollback como funcional sem efeito real e teste correspondente.
3. Integração indisponível deve falhar com erro explícito, não retornar sucesso sintético.
4. Executar os critérios de aceite definidos para a tarefa ativa no `TASK.md`.
5. Alterações exclusivamente documentais não exigem compilar um grafo legado; devem ser validadas quanto a encoding, links, consistência e Markdown.
6. Uma tarefa só pode ser marcada `completed` depois que todas as verificações aplicáveis passarem.
