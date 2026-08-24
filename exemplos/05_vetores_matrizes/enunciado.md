# 05 — Vetores e matrizes

Assunto: vetores 1D, matrizes 2D, inicialização por literal `{...}`/
`{{...}}`, índices sempre 0-baseados. A linguagem só suporta vetores de 3+
dimensões (ex.: `cubo:inteiro[2][2][2]`, ver manual) sem novidade
conceptual sobre o 2D — por isso não tem exemplo dedicado aqui.

## `analise_temperaturas.algo`

Regista até 31 temperaturas diárias e calcula média, máxima, mínima e
dias acima de um limiar.

Demonstra: **o tamanho de um vetor tem de ser conhecido em compilação**
— não pode ser `numeroDias` (lido do utilizador), por isso o vetor
declara sempre capacidade 31 e um `se numeroDias > CAPACIDADE_MAXIMA`
(assunto 03) corta o excesso; vetor literal de `cadeia` para os nomes dos
dias; `i mod 7` (assunto 02) para os nomes repetirem em ciclo além do 7º
dia; acumuladores dentro de `para` (assunto 04) agora a ler de um vetor
em vez de variáveis soltas.

## `tabuleiro_jogo_da_velha.algo`

Analisa um tabuleiro de jogo do galo 3x3 já preenchido: conta símbolos e
procura uma linha completa.

Demonstra: matriz 2D com literal `{{...}}` de `caracter`, índices
`tabuleiro[i][j]`, `para` aninhado dentro de `para`, concatenação
`cadeia + caracter` (assunto 01) para montar cada linha antes de a
imprimir de uma vez, e `sair` (assunto 04) para parar assim que encontra
uma linha vencedora.

## `verificador_stock.algo`

Procura um produto num inventário pequeno e devolve a quantidade em
stock.

Demonstra: dois vetores 1D **paralelos** (mesma posição = mesmo produto)
inicializados por literal, e o idioma de procura linear —
`para` + `se` + `sair` assim que encontra, com uma bandeira `booleano`
(assunto 04) para distinguir "não encontrado" de "encontrado com
quantidade zero".
