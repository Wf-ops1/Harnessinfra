# DEC-016 — Composição operacional obrigatória antes da release candidate

> **Estado:** aceita
> **Data:** 2026-08-29
> **Autoridade:** auditoria de retomada e autorização explícita do usuário para continuar

## Contexto

As Fases 0–6 e as tarefas F7.1–F7.3 entregaram e promoveram contratos, runtime, persistência,
providers configuráveis, tools confinadas, worktree, verificação, governança, recovery, evidence,
doctor, E2E externo, matriz e quality gates. A F7.1 comprovou o ciclo vertical por uma wheel instalada,
mas sua fixture monta explicitamente provider determinístico, tool router, worktree manager e
executores.

O caminho público permanece mais restrito: `harness run` resolve configuração e inicia o lifecycle
com registry de executores deliberadamente vazio, falhando antes de modelo ou tool. Esse
comportamento é seguro, porém não satisfaz sozinho a definição de MVP operacional. A F7.4 trata
empacotamento e portabilidade; a F7.5, como estava escrita, permitiria chamar a versão `0.x` de MVP
sem uma tarefa que conectasse as primitivas promovidas.

## Decisão

1. A ordem restante da Fase 7 passa a ser F7.4 → F7.C1 → F7.5.
2. A F7.4 continua responsável somente por empacotamento e portabilidade. Ela não pode introduzir
   wiring operacional oculto para antecipar a corretiva.
3. A F7.C1 deverá compor o workflow estável `new-feature` no caminho público instalado, usando as
   autoridades canônicas já promovidas para configuração, provider, tools, worktree, contexto,
   planejamento, verificação, aprovação, promoção, knowledge, evidence, cancelamento e rollback.
4. Configuração, credenciais, trust, policy, grants e aprovação ausentes continuam falhando fechado.
   A composição não pode registrar mock em produção, conceder confiança implícita, fabricar decisão
   humana ou transformar indisponibilidade em sucesso.
5. O E2E da F7.C1 deverá partir da wheel instalada em repositório Git externo descartável e acionar o
   caminho público, sem factory de lifecycle específica da fixture. Transporte externo pode usar
   servidor controlado no teste, desde que o adapter e a seleção sejam os mesmos de produção.
6. A F7.5 permanece bloqueada até F7.C1 ser promovida, reconciliada e verde em `main`.
7. Se a composição não puder ser entregue no escopo do MVP, a alternativa exige nova decisão
   explícita que retire a expressão “MVP operacional” da release; documentação não pode encobrir a
   ausência.

## Critérios mínimos da F7.C1

- `harness run new-feature` seleciona a composição canônica a partir de configuração válida;
- ausência de provider, tool, worktree, gate ou autoridade bloqueia antes do efeito correspondente;
- toda escrita permanece no worktree externo vinculado à execução;
- pause/resume usa o mesmo bundle, configuração e identidades persistidas;
- candidate, aprovação, promoção, knowledge e evidence seguem seus protocolos canônicos;
- cancelamento e rollback usam os controladores vinculados à mesma execução;
- nenhuma factory específica de teste replica o pipeline fora do código de produção;
- E2E externo, regressão integral, matriz F7.2 e gates F7.3 permanecem verdes.

## Consequências

- A release candidate não será apenas uma coleção de primitivas injetáveis.
- F7.4 pode consolidar package resources antes de F7.C1 consumir a wheel instalada.
- A composição ganha um gate próprio, rollback isolável e dossiê auditável.
- F7.5 passa a validar uma fronteira pública já promovida, em vez de introduzir wiring novo durante a
  preparação da release.

## Não escopo desta decisão documental

Esta decisão não implementa a F7.C1, não cria dossiê ativo, não altera produto, dependências, schemas,
defaults ou CI e não autoriza iniciar F7.4. Cada tarefa continua sujeita ao ciclo Git, ao gate `READY`
e à autorização nominal definidos no plano.
