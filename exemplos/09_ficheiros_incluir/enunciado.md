# 09 — Ficheiros incluídos

Assunto: `incluir "ficheiro.algo" como <alias>` (o `como <alias>` é
sempre obrigatório). Ao contrário dos assuntos anteriores, cada exemplo
aqui é um **par de ficheiros**: um `principal_*.algo` (com
`algoritmo`/`inicio`, o que se corre) e um ou dois `biblioteca_*.algo`
(só declarações — sem `algoritmo` nem `inicio`, seguindo a regra do
manual). Corre-se sempre a partir desta pasta, para o caminho relativo
do `incluir` resolver: `algo executa principal_geometria.algo`.

## `principal_geometria.algo` + `biblioteca_geometria.algo`

`incluir ... como geo` — as funções (`geo.areaCirculo`,
`geo.perimetroCirculo`, `geo.areaRetangulo`) do ficheiro incluído só
ficam disponíveis com o prefixo do alias; a `constante` global `PI`
continua disponível diretamente, sem prefixo.

## `principal_calculos.algo` + `biblioteca_financas.algo` +
`biblioteca_estatistica.algo`

Dois `incluir`, cada um com o seu próprio alias (`como financas`, `como
estatistica`) — evita colisão de nomes entre os dois ficheiros.
Reaproveita vetores (assunto 05) passados às funções da biblioteca de
estatística.

## `principal_inventario.algo` + `biblioteca_inventario.algo`

`incluir ... como inv`, mas com uma `estrutura Produto` e uma variável
global `contadorProdutosCriados` no ficheiro incluído.

Demonstra: o alias só se aplica a **funções** (`inv.criarProduto(...)`)
— a estrutura `Produto` usa-se diretamente (`p1:Produto`) e a variável
global lê-se diretamente (`contadorProdutosCriados`), ambas sem `inv.`.
Confirmado em runtime: o contador acumula
corretamente entre as duas chamadas a `criarProduto`, feitas a partir do
programa principal mas a mutar a global do ficheiro incluído.
