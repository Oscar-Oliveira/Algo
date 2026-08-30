# 08 — Bibliotecas

Assunto: `importar`, e as três bibliotecas embutidas (`Matematica`,
`Cadeia`, `Conversao`).

## `calculadora_cientifica.algo`

Menu de operações matemáticas sobre um número.

Demonstra: toda a `Matematica` — `raiz`, `absoluto`, `piso`, `teto`,
`aleatorio`, `potencia` — dentro de um `escolher/caso` (assunto 03).

## `processador_texto.algo`

Analisa uma frase: maiúsculas/minúsculas, invertida, teste de
palíndromo, metades, separação em palavras.

Demonstra: toda a `Cadeia` — `comprimento`, `maiusculas`, `minusculas`,
`inverter`, `subcadeia`, `caracter`, `procurar`, `substituir`,
`dividir`. `dividir` só tem o tamanho real conhecido em runtime, e
inicializar um vetor de tamanho fixo (assunto 05) com o resultado exige
que o nº de partes bata certo com o tamanho declarado — por isso o
exemplo pede ao utilizador um número de palavras conhecido à partida
(exatamente 4), em vez de tentar dividir a frase livre já lida.

## `conversor_universal.algo`

Converte entre os 5 tipos primitivos e cifra uma letra por código ASCII
(cifra de César).

Demonstra: toda a `Conversao` — `paraTexto`, `paraInteiro`,
`paraDecimal`, `paraBooleano`, `paraCaracter`, `paraAscii`, `deAscii`.
`conversao.paraTexto` finalmente resolve a lacuna documentada no
assunto 01 (`+` não converte número para texto). `paraBooleano`
reconhece `"falso"`/`"f"`/`"false"`/`"não"`/`"nao"`/`"n"`/`"0"` (sem
distinguir maiúsculas) como negativo — a própria palavra portuguesa
"não" tem tratamento explícito, para não cair na truthiness nativa do
Python (texto não vazio → verdadeiro), que seria uma armadilha numa
linguagem cujo código-fonte é todo em português.
