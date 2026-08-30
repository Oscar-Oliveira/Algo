# 03 — Condicionais

Assunto: `se`/`senao se`/`senao`, `se` aninhado dentro de `se`, e
`escolher`/`caso`/`contrario`. Ainda sem ciclos — cada programa continua a
correr uma única vez, do início ao fim.

## `classificador_imc.algo`

Calcula o IMC (Índice de Massa Corporal) e classifica-o, e classifica
também a altura à parte.

Demonstra: uma cadeia `se / senao se / senao se / senao` com 4
alternativas exclusivas, avaliadas por ordem; reaproveita `^` e `/`
(decimal) do assunto 02.

## `calculadora_portes_envio.algo`

Calcula o custo de envio de uma encomenda consoante peso, distância e
estatuto de membro.

Demonstra: `se` **aninhado** dentro de `se` (não só cadeias `senao se`
lado a lado), e condições compostas com `e`/`ou` do assunto 02 dentro da
própria condição do `se` (`pesoKg <= 1.0 e distanciaKm <= 50.0`).

## `menu_operacoes.algo`

Menu de calculadora de dois números inteiros, com uma opção por operação.

Demonstra: `escolher/caso`, incluindo um `caso 7, 8` com vários valores a
partilhar o mesmo corpo (tal como o `caso 6, 7` do manual), `contrario`
para opção inválida, e reaproveita `+`/`-`/`*`/`/`/`div`/`mod` do
assunto 02 — `/` entre dois `inteiro` continua a devolver sempre
`decimal` (regra de `semantics.py:_tipo_binop`, já vista no assunto 02),
mesmo dentro de um `escolher` sobre inteiros.
