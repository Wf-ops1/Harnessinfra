# Auditoria Técnica da Estrutura, Fluxos e Pendências

> **Status: diagnóstico do protótipo; não é certificação operacional**

## 1. Método

A auditoria considera uma capacidade existente somente quando o código produz o efeito declarado e
há teste correspondente. Nomes de classes, YAMLs, diagramas e estados da FSM são evidência de design,
mas não substituem conectividade, isolamento, side effects reais ou falha segura.

## 2. Consistência da estrutura

| Item documentado anteriormente | Estado observado | Correção |
|---|---|---|
| `task.md` | O arquivo rastreado é `TASK.md` | Referências normalizadas |
| `contracts/` na raiz | Ausente | Contratos reais ficam em `src/ai_engineering_harness/contracts/` |
| `policies/` na raiz | Ausente | Defaults ficam em `src/ai_engineering_harness/defaults/policies/` |
| `graphs/specs/` na raiz | Ausente | Defaults ficam no pacote; specs locais ficam sob `.harness/` após init |
| `observability/log_integrity.py` | Ausente | Integridade está em `observability/audit.py` |
| Contagem fixa de testes | Ficava obsoleta após cada fase | Relatórios agora registram o checkpoint a que a contagem pertence |

## 3. FSM observada

Os estados e transições estão implementados em
[state_machine.py](../src/ai_engineering_harness/runtime/state_machine.py). O caminho principal atual
é:

```text
INITIATED
  -> CONTEXT_ASSEMBLING
  -> GENERATING_PLAN
  -> EXECUTING
  -> VERIFYING
  -> (EXECUTING/VERIFYING em retry)
  -> AWAITING_APPROVAL ou PROMOTING
  -> REINDEXING
  -> KNOWLEDGE_SYNC
  -> GENERATING_EVIDENCE
  -> COMPLETED
```

O grafo acima descreve transições de software, não efeitos garantidos. Em particular:

- `EXECUTING` recebe resposta sintética de provider e não comprova edição;
- `PROMOTING` é chamado em dry-run;
- `REINDEXING` recebe mock AST;
- `COMPLETED` pode conter SHA sintético.

## 4. Matriz de comandos

| Comando | Código existe | Efeito real comprovado | Classificação |
|---|---:|---:|---|
| `harness init` | Sim | Cria/copia scaffold local | Implementado como base |
| `harness doctor` | Sim | Apenas renderiza resultados pré-aprovados | Simulado |
| `harness compile` | Sim | Lê YAML e grava JSON | Experimental |
| `harness index` | Sim | Grava snapshot de dados fabricados | Simulado |
| `harness run` | Sim | Grava artefatos locais do fluxo | Experimental/simulado |
| `harness status` | Sim | Lê arquivo de estado | Implementado como leitura local |
| `harness inspect` | Sim | Lê estado, audit e aprovação | Experimental |
| `harness approve` | Sim | Persiste decisão | Parcial; não retoma o fluxo |
| `harness verify` | Sim | Executa subprocessos selecionados | Experimental |
| `harness audit` | Sim | Valida hash chain local | Implementado como mecanismo local |
| `harness rollback` | Sim | Eventos locais e Git opcional | Experimental/inseguro |

## 5. Riscos prioritários

| Prioridade | Risco | Causa atual | Fase responsável |
|---|---|---|---|
| P0 | Alteração fora de isolamento | Worktree real ausente e Serena sem confinamento | F3.6/F5 |
| P0 | Execução arbitrária de shell | Terminal recebe string e usa `shell=True` | F3.5/F5 |
| P0 | Sucesso sem efeito | Providers, promoção e memória sintéticos | F2/F3/F4 |
| P0 | Diagnóstico enganoso | Doctor retorna saudável incondicionalmente | F6.5 |
| P1 | Grafo não governa runtime | Dois compiladores e sequência fixa | F1/F2 |
| P1 | Aprovação sem resume seguro | Estado e protocolo incompletos | F2/F5 |
| P1 | Evidência insuficiente | Pode registrar identificadores sintéticos | F6/F7 |
| P1 | Ausência de CI obrigatória | Gates somente locais | F0.6 |

## 6. Gates para considerar o produto operacional

- instalação em ambiente limpo e em repositório externo;
- nenhum adapter simulado registrado no runtime;
- doctor falha quando dependência real estiver ausente;
- toda escrita ocorre dentro de worktree criado por Git;
- comando de ferramenta usa argv, allowlist, cwd confinado e `shell=False`;
- gate obrigatório não executado bloqueia;
- aprovação pausa e retoma após reinício;
- promoção produz candidate SHA e promoted SHA reais;
- rollback usa `git revert` e reexecuta gates;
- E2E cobre sucesso, falha, retry, resume, promoção e rollback sem mocks;
- CI Windows/Linux e artefato de release validados.

Os critérios completos estão no
[plano de implementação](plano_implementacao_harness_operacional.md).
