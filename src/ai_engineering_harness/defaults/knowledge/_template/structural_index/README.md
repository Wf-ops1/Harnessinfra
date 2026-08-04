# Structural Index Persistence & Operational Lifecycle (.knowledge/structural_index/)

Este diretório especifica a mecânica operacional do **Índice Estrutural Persistente** vinculado estritamente ao `git_commit_sha`.

## 🔄 Protocolo de Durabilidade em 4 Etapas:
1. **Gravar `current.tmp`**
2. **`flush` + `os.fsync(current.tmp)`**
3. **`os.replace(current.tmp, current.json)`**
4. **`os.fsync(parent_directory)`**

## 🛡️ As 3 Invariantes Fundamentais de Integridade:
1. **`snapshots/<commit_sha>` já existe:** Aceitar somente se o `merkle_root` for idêntico; caso contrário, sinalizar conflito/corrupção.
2. **`current.json` inválido:** Buscar apenas snapshot `ready`, exigir `commit_sha` igual ao Git atual e validar Merkle antes de servir.
3. **Nenhum snapshot válido para o commit atual:** NUNCA servir um commit diferente diretamente ao agente. Executar reindexação limpa.
