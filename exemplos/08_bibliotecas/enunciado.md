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
assunto 01 (`+` não converte número para texto).

### Achado ao testar `conversao.paraBooleano`

`conversao.paraBooleano("não")` devolve **`verdadeiro`**, não `falso`.
A função só reconhece `"falso"`/`"f"`/`"false"` (sem distinguir
maiúsculas) como negativo — qualquer outro texto não vazio segue a
truthiness nativa do Python, incluindo a própria palavra portuguesa
"não". Numa linguagem cujo código-fonte inteiro é em português, isto é
mais armadilha do que pareceria numa biblioteca em inglês (onde "no" ou
"not" também não seriam reconhecidos, mas não têm o mesmo peso
enganador). Confirmado em runtime; ver conversa para decisão sobre se
isto deve ser corrigido ou só documentado como limitação conhecida.
