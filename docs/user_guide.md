# Manual de Operação e Guia do Usuário — AI-Engineering-Harness

O **AI-Engineering-Harness** é um motor agentic local-first, instalável via `pip install ai-engineering-harness`, capaz de executar workflows completos de engenharia sobre qualquer repositório de software através de uma pasta leve `.harness/`.

---

## 🚀 Instalação e Inicialização

```bash
# 1. Instalar o pacote
pip install -e .

# 2. Inicializar a pasta .harness/ no repositório do seu projeto
harness init

# 3. Testar a saúde do ambiente (Probe de 6 Estágios)
harness doctor
```

---

## 🛠️ Principais Comandos CLI

- `harness init`: Cria a estrutura de metadados `.harness/` no projeto local.
- `harness doctor`: Testa Serena MCP, Codebase-Memory MCP, Git e LLM Providers.
- `harness compile <spec.yaml>`: Compila um grafo YAML em artefato MAF JSON em `.harness/state/compiled/`.
- `harness index`: Atualiza o snapshot AST vinculado ao Git Commit SHA.
- `harness run <workflow>`: Executa um workflow agentic autônomo.
- `harness status <exec_id>`: Consulta o status da FSM de uma execução em andamento.
- `harness approve <exec_id>`: Aprova a promoção de alterações em estado `AWAITING_APPROVAL`.
- `harness verify`: Executa as verificações determinísticas poliglotas aplicáveis ao projeto.
- `harness audit <exec_id>`: Valida a integridade da Hash Chain dos logs de auditoria.
- `harness rollback <exec_id>`: Executa a reversão em 2 fases (Código / Efeitos).

---

## 🏛️ Separação Harness vs Produto

- **Motor Instalado (`src/ai_engineering_harness/`):** Contém o runtime, compilador, governança e verificadores.
- **Projeto Local (`.harness/`):** Guarda unicamente a configuração, conhecimento (`knowledge/`), estado (`state/`) e artefatos (`artifacts/`).
