# 02 — Operadores

Assunto: operadores relacionais (`==`, `<>`, `<`, `>`, `<=`, `>=`), lógicos
(`e`, `ou`, `nao`) e aritméticos (`div`, `mod`, `^`, e precedência entre
`*`/`/` e `+`/`-`). Continua sem `se`/ciclos — cada condição fica guardada
num `booleano` com nome próprio e é impressa, em vez de ramificar.

## `avaliacao_elegibilidade.algo`

Avalia se um candidato é elegível para uma bolsa de estudo, combinando
critério de idade, média de notas e situação social.

Demonstra: `>=`/`<=`/`<` sobre `inteiro`/`decimal`, `e`/`ou` a combinar
booleanos, e `nao` — inclui o caso deliberado
`nao dentroDaFaixaEtaria e mediaSuficiente e cumpreCriterioSocial`, que só
faz sentido porque `nao` tem precedência mais alta que `e` (liga só a
`dentroDaFaixaEtaria`, não à condição toda).

## `distribuicao_equipas.algo`

Distribui jogadores de um torneio por equipas e calcula a área/perímetro
do campo quadrado onde vão jogar.

Demonstra: `div`/`mod` (exigem os dois lados `inteiro`), `^` para a área,
e que `*`/`/` têm precedência sobre `+`/`-` sem precisar de parênteses
(`numeroEquipasCompletas * tamanhoEquipa * PRECO... + jogadoresDeFora *
PRECO...`).

## `comparador_orcamentos.algo`

Compara dois orçamentos de fornecedores e verifica se cabem num orçamento
máximo.

Demonstra: bateria completa de relacionais sobre `decimal`
(`==`/`<>`/`<`/`<=`), `nao` sobre um resultado já calculado
(confirmado em runtime como equivalente a `<>`), e reforça a concatenação
de texto (`+`) do assunto 01 no título da comparação.
