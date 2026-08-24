# 09 — Ficheiros incluídos

Assunto: `incluir "ficheiro.algo"` e `incluir "ficheiro.algo" como
<alias>`. Ao contrário dos assuntos anteriores, cada exemplo aqui é um
**par de ficheiros**: um `principal_*.algo` (com `algoritmo`/`inicio`,
o que se corre) e um ou dois `biblioteca_*.algo` (só declarações — sem
`algoritmo` nem `inicio`, seguindo a regra do manual). Corre-se sempre a
partir desta pasta, para o caminho relativo do `incluir` resolver:
`algo executa principal_geometria.algo`.

## `principal_geometria.algo` + `biblioteca_geometria.algo`

`incluir` **sem** alias — as funções (`areaCirculo`, `perimetroCirculo`,
`areaRetangulo`) e a `constante` global `PI` do ficheiro incluído passam
a estar disponíveis diretamente, sem prefixo.

## `principal_calculos.algo` + `biblioteca_financas.algo` +
`biblioteca_estatistica.algo`

Dois `incluir`, ambos **com** alias (`como financas`, `como
estatistica`) — evita colisão de nomes entre os dois ficheiros, e seria
avisado pelo linter a partir do 2º `incluir` sem alias no mesmo
programa. Reaproveita vetores (assunto 05) passados às funções da
biblioteca de estatística.

## `principal_inventario.algo` + `biblioteca_inventario.algo`

`incluir ... como inv`, mas com uma `estrutura Produto` e uma variável
global `contadorProdutosCriados` no ficheiro incluído.

Demonstra: o alias só se aplica a **funções** (`inv.criarProduto(...)`)
— a estrutura `Produto` usa-se diretamente (`p1:Produto`) e a variável
global lê-se diretamente (`contadorProdutosCriados`), ambas sem `inv.`.
Confirmado em runtime: o contador acumula
corretamente entre as duas chamadas a `criarProduto`, feitas a partir do
programa principal mas a mutar a global do ficheiro incluído.
