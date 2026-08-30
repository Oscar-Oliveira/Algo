# 8. Bibliotecas

A linguagem tem três bibliotecas embutidas: `Matematica`, `Cadeia`,
`Conversao`. Cada uma só fica disponível depois de `importar`, no topo
do ficheiro (antes de qualquer `funcao`/`procedimento`/`inicio`):

```algo
algoritmo "Exemplo"

importar Matematica

inicio
    escrever(matematica.raiz(16))
```

- `importar` usa o nome capitalizado por convenção (`Matematica`), mas
  não é sensível a maiúsculas/minúsculas (`importar matematica`
  funciona também).
- Chamar uma função é sempre `nome_em_minusculas.funcao(...)`,
  independentemente de como escreveste o `importar`.
- Usar `matematica.raiz(...)` sem `importar Matematica` primeiro é erro
  de compilação, não erro em runtime.

`importar` (biblioteca embutida) é uma coisa diferente de `incluir`
(outro ficheiro `.algo` teu) — capítulo 9.

## 8.1 `Matematica`

| Função | Assinatura | Nota |
|---|---|---|
| `raiz` | `(numérico):decimal` | raiz quadrada |
| `potencia` | `(numérico, numérico):decimal` | ver capítulo 2 — sempre `decimal`, mesmo `matematica.potencia(2, 10)` |
| `absoluto` | `(numérico):mesmo tipo do argumento` | `absoluto(-5)` é `inteiro`; `absoluto(-5.5)` é `decimal` |
| `piso` | `(numérico):inteiro` | arredonda para baixo |
| `teto` | `(numérico):inteiro` | arredonda para cima |
| `aleatorio` | `(inteiro, inteiro):inteiro` | inteiro aleatório, **incluindo os dois limites** |

```algo
inicio
    escrever(matematica.raiz(16))          // 4.0
    escrever(matematica.absoluto(-5))      // 5       -- inteiro
    escrever(matematica.absoluto(-5.5))    // 5.5     -- decimal
    escrever(matematica.piso(3.9))         // 3
    escrever(matematica.teto(3.1))         // 4

    dado:inteiro = matematica.aleatorio(1, 6)   // 1 a 6, ambos possíveis
```

`matematica.aleatorio(a, b)` com `a > b` é erro em runtime (mensagem
amigável), não um resultado silenciosamente vazio ou trocado.

## 8.2 `Cadeia`

| Função | Assinatura | Nota |
|---|---|---|
| `comprimento` | `(cadeia):inteiro` | número de caracteres |
| `maiusculas` / `minusculas` | `(cadeia):cadeia` | |
| `inverter` | `(cadeia):cadeia` | |
| `subcadeia` | `(cadeia, inteiro, inteiro):cadeia` | `(s, início, fim)` — 0-baseado, `fim` **exclusivo** |
| `caracter` | `(cadeia, inteiro):caracter` | posição 0-baseada |
| `procurar` | `(cadeia, cadeia):inteiro` | posição da 1ª ocorrência, ou `-1` se não encontrar |
| `substituir` | `(cadeia, cadeia, cadeia):cadeia` | substitui **todas** as ocorrências |
| `dividir` | `(cadeia, cadeia):cadeia[]` | separa por texto — **devolve um vetor** |

```algo
inicio
    s:cadeia = "Ola Mundo"
    escrever(cadeia.comprimento(s))            // 9
    escrever(cadeia.maiusculas(s))             // OLA MUNDO
    escrever(cadeia.subcadeia(s, 0, 3))        // Ola   -- índices 0,1,2 (3 é exclusivo)
    escrever(cadeia.caracter(s, 4))            // M
    escrever(cadeia.procurar(s, "Mundo"))      // 4
    escrever(cadeia.procurar(s, "xyz"))        // -1  -- não encontrado, não é erro
```

`dividir` é a única função de biblioteca que devolve um vetor — o
tamanho declarado do lado esquerdo tem de bater certo com o número de
partes real, verificado em runtime (capítulo 5):

```algo
inicio
    partes:cadeia[3] = cadeia.dividir("a,b,c", ",")
    escrever(partes[0], " ", partes[1], " ", partes[2])   // a b c
```

`procurar`/`substituir`/`dividir` rejeitam com erro amigável um texto
vazio no argumento relevante (o que se procura, o que se substitui, o
separador) — `str.find("")`/`split("")` do Python dariam resultados
estranhos (uma posição "encontrada" em todo o lado, ou um crash) sem
valor pedagógico nenhum.

## 8.3 `Conversao`

Converte entre os cinco tipos primitivos. Uma conversão que não faz
sentido (`conversao.paraInteiro("abc")`) dá erro amigável em runtime,
nunca um traceback cru do Python.

| Função | Assinatura |
|---|---|
| `paraTexto` | `(qualquer primitivo):cadeia` |
| `paraInteiro` | `(qualquer primitivo):inteiro` — trunca um `decimal` em direção a zero |
| `paraDecimal` | `(qualquer primitivo):decimal` |
| `paraBooleano` | `(qualquer primitivo):booleano` — ver nota abaixo |
| `paraCaracter` | `(cadeia):caracter` — exige exatamente 1 símbolo |
| `paraAscii` | `(caracter):inteiro` |
| `deAscii` | `(inteiro):caracter` |

```algo
inicio
    escrever(conversao.paraTexto(42))          // "42"
    escrever(conversao.paraInteiro(3.9))       // 3   -- trunca, não arredonda
    escrever(conversao.paraDecimal("3.14"))    // 3.14
    escrever(conversao.paraAscii('A'))         // 65
    escrever(conversao.deAscii(65))            // A
```

### `paraBooleano` só reconhece um punhado de textos como falso

```algo
inicio
    escrever(conversao.paraBooleano("falso"))     // falso
    escrever(conversao.paraBooleano("nao"))       // falso
    escrever(conversao.paraBooleano(0))           // falso  -- inteiro 0
    escrever(conversao.paraBooleano("0"))         // falso  -- texto "0"
    escrever(conversao.paraBooleano("qualquer coisa"))  // verdadeiro
```

Só o texto `"falso"`/`"f"`/`"false"`/`"não"`/`"nao"`/`"n"`/`"0"` (sem
diferenciar maiúsculas, com espaços à volta ignorados) converte para
`falso`. **Qualquer outro texto não vazio converte para `verdadeiro`**,
porque a regra por baixo é a truthiness nativa do Python (`bool(x)`), e
uma cadeia de texto não vazia é sempre truthy, seja qual for o seu
conteúdo — só a lista fixa acima é a exceção deliberada a essa regra.

## Exemplo completo

```algo
algoritmo "AnalisadorDeFrase"

importar Cadeia
importar Matematica

inicio
    frase:cadeia
    escrever("Escreve uma frase: ")
    ler(frase)

    escrever("Maiúsculas: ", cadeia.maiusculas(frase))
    escrever("Comprimento: ", cadeia.comprimento(frase))
    escrever("Invertida: ", cadeia.inverter(frase))

    // 'dividir' devolve um vetor cujo tamanho REAL só se conhece em
    // runtime -- o tamanho declarado aqui tem de bater certo exatamente
    // com o número de palavras da frase digitada (capítulo 5)
    palavras:cadeia[3] = cadeia.dividir(frase, " ")
    escrever("Primeira palavra: ", palavras[0])

    raizComprimento:decimal = matematica.raiz(cadeia.comprimento(frase))
    escrever("Raiz quadrada do comprimento: ", raizComprimento)
```
