# 07 — Estruturas

Assunto: `estrutura`, acesso a campo com `.`, estruturas aninhadas,
estrutura sempre aliasada como parâmetro vs `ref` para reatribuição
completa, vetor de estruturas, campo do próprio tipo (estrutura
recursiva) e comparação com `nulo`.

## `catalogo_produtos.algo`

Gere um catálogo de produtos: valor total do inventário, produto mais
caro, aplicar desconto a todos.

Demonstra: vetor de `estrutura` (`Produto[3]`), acesso a campo por índice
(`catalogo[i].preco`), e funções/procedimentos sobre vetor de estruturas
(assunto 06) — `aplicarDesconto` muta os preços de todo o catálogo do
próprio vetor do chamador sem precisar de `ref` (vetor já é aliasado por
omissão; `ref` só seria preciso para reatribuir o parâmetro `produtos`
a outro vetor inteiro).

## `geometria_pontos.algo`

Pontos, segmentos, e distância entre dois pontos.

Demonstra: `estrutura` aninhada dentro de outra (`Segmento` tem dois
campos `Ponto`), que uma `estrutura` é sempre aliasada como parâmetro —
`deslocar` muta um campo do `Ponto` do chamador **sem** `ref` — e que
`ref` só é necessário para uma **reatribuição completa** do parâmetro
(`reiniciar`), e reforça que `matematica.raiz` só existe a partir do
assunto 08: a raiz quadrada é aproximada aqui com o método de Newton,
escrito à mão com `para` (assunto 04).

## `lista_ligada_fixa.algo`

Uma lista ligada de tamanho fixo (3 nós), construída de trás para a
frente e percorrida com `enquanto no <> nulo fazer`.

Demonstra: um campo de estrutura do **próprio tipo** (`seguinte:No`),
válido por ficar `nulo` por omissão em vez de recursão infinita; como
ALGO não tem alocação dinâmica, cada `nó.seguinte = outroNo` é uma **cópia** do resto
da cadeia (não um ponteiro partilhado), por isso a lista tem de ser
montada de trás para a frente — testado e confirma-se que soma/conta os
3 nós corretamente.
