# Graph Compiler (`compiler/`)

O **Graph Compiler** é o árbitro de design-time do Harness.

Ele valida a teia de dependências entre especificações de grafos (`graphs/specs/*.yaml`), contratos tipados (`contracts/**/*.py`) e políticas (`policies/*.yaml`), e emite as definições imutáveis do MAF em `graphs/compiled/*.maf.json`.

---

## Como Executar

Na raiz do repositório `ai-engineering-harness`:

```bash
python compiler/compile.py --graph graphs/specs/new-feature.yaml
```

### Saída Esperada:
1. Validação dos schemas Pydantic de entrada e saída por nó.
2. Validação da consistência das permissões de ferramentas por nó.
3. Injeção determinística de verification gates de `policies/verification_policy.yaml`.
4. Geração do arquivo JSON imutável em `graphs/compiled/new-feature.maf.json`.
