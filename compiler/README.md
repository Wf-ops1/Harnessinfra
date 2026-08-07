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

O único destino é `.harness/state/compiled/<workflow>.json`, no formato incompatível
`CompiledGraphArtifact` 2.0. O envelope contém o grafo canônico completo, contratos e políticas
resolvidos, digests de grafo/políticas/contratos, manifest portátil das fontes e a lista declarativa
de capabilities efetivamente permitidas. Não contém timestamp nem paths absolutos.

A serialização é JSON UTF-8 canônico e determinístico. A publicação usa um arquivo temporário
exclusivo no mesmo diretório, `flush`, `fsync` e substituição atômica; uma falha anterior à
substituição preserva o último artefato válido. Antes de qualquer execução, o `MAFAdapter` exige
compatibilidade exata das versões, recomputa a integridade e relê todas as fontes do manifest.
Artefatos 1.0 devem ser recompilados; não existe upgrade ou fallback silencioso.

O wrapper não lê YAML diretamente, não injeta nós e não possui pipeline de compilação próprio.
`required_capabilities` é somente uma declaração compilada: disponibilidade de adapters e
autorização de runtime pertencem a fases posteriores.
