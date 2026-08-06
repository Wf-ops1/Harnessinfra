# Graph Compiler compatibility wrapper

`compiler/compile.py` é apenas um wrapper de compatibilidade. A única implementação pertence a
`ai_engineering_harness.compiler.GraphCompiler` e aplica os contratos tipados, o registry seguro de
contratos e o registry estrito de políticas antes de produzir qualquer arquivo.

---

## Como Executar

Na raiz do projeto inicializado:

```bash
python <caminho-do-harness>/compiler/compile.py --graph .harness/graphs/specs/new-feature.yaml
```

O único destino é `.harness/state/compiled/<workflow>.json`, no formato
`CompiledGraphArtifact`. O wrapper não lê YAML diretamente, não injeta nós e não possui pipeline de
compilação próprio.
