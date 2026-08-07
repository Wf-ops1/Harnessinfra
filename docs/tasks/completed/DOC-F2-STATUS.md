# DOC-F2-STATUS — Dossiê concluído

> **Estado:** arquivo histórico imutável.
> **Fonte:** `TASK.md` no commit `d48151b752aa373756c46bfee58932fa5abf4bf5`.
> **Integridade do payload:** `sha256:5ed7a17ceaa53e0c8b30653f7f616aca80225b64497b80652d8996cd5e1f5183`.

<!-- TASK_LEDGER_PAYLOAD_START -->
### DOC-F2-STATUS — Alinhar documentação pública pós-F2.5

| Campo | Detalhe |
|---|---|
| **Status** | `completed e promovida` — gate documental `READY → COMPLETED`; PR #12 mesclado e CI pós-merge verde |
| **Objetivo** | Corrigir a matriz pública que ainda descreve o compilador e o runtime como estavam antes das entregas F1/F2, preservando os limites reais de F2.6–F7 |
| **Branch exclusiva** | `docs/readme-f2-status`, criada de `main == origin/main == 2aa324b` após CI pós-merge verde da F2.5 |
| **Executor** | `Codex`, único escritor, sob autorização explícita do usuário `execute` |
| **Checkpoints** | `checkpoint/docs-f2-status-ready^{}` → `283a33ea06fa4253c29861f461989f6d800bdb40`; `checkpoint/docs-f2-status-complete^{}` → `9d679a5d978806048b0056a42becdae92f174e29` |
| **Promoção** | [PR #12](https://github.com/Wf-ops1/Harnessinfra/pull/12) → merge `f23d74d0ccc9f377628e0358a527836ee99aba27`; runs `31210284986` e `31210521957`, ambos `completed/success` com 11/11 checks |

```yaml
defensibility:
  task_id: "DOC-F2-STATUS"
  gate: "READY"
  executor: "Codex"
  authorized_at: "2026-08-07T16:05:00-03:00"
  problem_statement: >-
    README.md ainda afirma que existem dois caminhos de compilação, sequência fixa no runtime e
    retomada apenas planejada, embora F1.4, F2.3, F2.4 e F2.5 já estejam implementadas, testadas e
    promovidas; o documento subestima o estado real e diverge do painel de execução.
  evidence:
    - command: "inspeção da matriz de capacidade do README e comparação com TASK/PRs #6-#11"
      observed: >-
        linhas de compilação e runtime permanecem no baseline anterior; F2.5 integra main em
        2aa324b e o run pós-merge 31209619778 concluiu 11/11 checks com success
  baseline:
    branch: "docs/readme-f2-status"
    head: "2aa324b394d9ffcfa0b8d0f9ba011f02f5a96727"
    status: "clean; main == origin/main no momento da criação"
    checkpoint: "merge F2.5 2aa324b; CI pós-merge 31209619778 success"
  frozen_scope:
    allowed:
      - "README.md — introdução, roadmap e matriz de capacidade"
      - "TASK.md — promoção observada, gate, resultado e próxima ação"
    excluded:
      - "src/, compiler/, tests/, .github/, defaults, schemas, pyproject.toml e uv.lock"
      - "qualquer implementação F2.6, F3, F4, F5, F6, F7 ou efeito operacional novo"
      - "remoção de avisos sobre providers, tools, worktree, promoção, doctor e rollback simulados"
  frozen_acceptance:
    - command: >-
        uv run python -m pytest tests/unit/test_documentation.py tests/unit/test_encoding.py -q
      expected: "documentação e encoding verdes, incluindo links e matriz"
    - command: >-
        rg -n "dois caminhos de compilação|sequência fixa|Execução persistida e retomável dirigida pelo artefato na F2" README.md
      expected: "exit 1; claims anteriores ausentes"
    - command: "git diff --check; git diff --name-only 2aa324b"
      expected: "somente README.md e TASK.md; zero alteração de produto"
  rollback:
    triggers:
      - "documentação declarar provider/tool/worktree/promoção/doctor/rollback como operacional"
      - "qualquer arquivo fora do allowlist mudar ou teste documental falhar"
    procedure: >-
      antes do commit inverter somente os hunks documentais via apply_patch; depois do commit usar
      git revert do commit exclusivo; nunca resetar ou descartar trabalho preexistente
    verify: "git status, diff de escopo, testes documentais/encoding e git diff --check"
```

#### Resultado verificado de DOC-F2-STATUS

| Evidência | Resultado observado |
|---|---|
| README | Introdução e matriz reconhecem compilador único, artefato 2.0, execução por arestas, storage concorrente, FSM event-sourced e lifecycle retomável F2.5 |
| Limites preservados | Retry F2.6, providers/tools/worktree F3, contexto/verificação F4, governança F5, observabilidade/recovery F6 e release F7 continuam incompletos ou planejados |
| Testes documentais | `8 passed, 6 subtests passed` em `test_documentation.py` e `test_encoding.py` |
| Busca negativa | Zero ocorrência dos três claims obsoletos congelados; `rg` exit 1 como esperado |
| Encoding e estrutura | README/TASK decodificam em UTF-8 estrito; links, newline, fences e matriz aprovados |
| Escopo | Somente `README.md` e `TASK.md` diferem de `2aa324b`; `src`, `compiler`, `tests`, `.github`, dependências e lockfile permanecem byte-idênticos |
| Qualidade do diff | `git diff --check` exit 0; nenhuma implementação F2.6 ou capacidade operacional nova foi adicionada |

**Fechamento remoto comprovado:** PR #12 mesclado por merge commit `f23d74d`; o run de PR
`31210284986` e o run pós-merge `31210521957` concluíram os 10 jobs de matriz e `CI required` com
`success`. A branch remota documental foi preservada e a F2.6 não foi iniciada.

---
<!-- TASK_LEDGER_PAYLOAD_END -->
