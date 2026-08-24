# 2. Operadores

## 2.1 Aritméticos

| Operador | Significado | Exige | Resultado |
|---|---|---|---|
| `+` | soma | ambos numéricos | `decimal` se um dos lados for `decimal`, senão `inteiro` |
| `+` | concatenação | ambos texto (`cadeia`/`caracter`) | `cadeia` |
| `-` `*` | subtração / multiplicação | ambos numéricos | `decimal` se um dos lados for `decimal`, senão `inteiro` |
| `/` | divisão | ambos numéricos | sempre `decimal`, mesmo `4 / 2` |
| `div` | divisão inteira | ambos `inteiro` | `inteiro` |
| `mod` | resto da divisão inteira | ambos `inteiro` | `inteiro` |
| `^` | potência | ambos numéricos | ver 2.4 |

```algo
inicio
    escrever(7 / 2)        // 3.5  -- '/' é sempre decimal
    escrever(7 div 2)      // 3
    escrever(7 mod 2)      // 1
```

`+`/`-`/`*`/`/` não existem entre `cadeia`/`caracter` e um número — ver
[capítulo 1](01-Introducao-e-Tipos.md#17--não-converte-números-para-texto).
`div`/`mod` só aceitam `inteiro` dos dois lados (não há "divisão inteira
de decimais" na linguagem).

### `div`/`mod` com operandos negativos

`div`/`mod` truncam em direção a zero (como a divisão inteira ensinada
em C/Java/a maioria dos cursos introdutórios) — **não** como `//`/`%` do
Python, que arredondam para menos infinito:

```algo
inicio
    escrever(-7 div 2)     // -3   (Python -7 // 2 daria -4)
    escrever(-7 mod 2)     // -1   (Python -7 % 2 daria 1)
    escrever(7 div -2)     // -3
    escrever(7 mod -2)     // 1
```

O sinal de `mod` acompanha sempre o sinal do primeiro operando (do
dividendo), e vale sempre `a == (a div b) * b + (a mod b)`.

## 2.2 Relacionais e igualdade

`==`  `<>`  `<`  `>`  `<=`  `>=` — todos devolvem `booleano`.

- `==`/`<>` comparam dois numéricos (`inteiro`/`decimal` cruzados
  incluídos: `1 == 1.0` é `verdadeiro`), dois textos
  (`cadeia`/`caracter` cruzados incluídos), ou `nulo` com uma variável de
  tipo `estrutura` (capítulo 7). Comparar tipos incompatíveis
  (`5 == "5"`, por exemplo) é erro de compilação.
- `<`/`>`/`<=`/`>=` aceitam dois numéricos ou dois textos — texto compara
  por ordem de código Unicode, não ordem alfabética portuguesa (ex.:
  `"Z" < "a"` é `verdadeiro`, porque maiúsculas vêm antes de minúsculas
  em Unicode).
- Duas `estrutura` comparam-se campo a campo com `==`/`<>` (não por
  identidade) — ver capítulo 7.

**Não é possível encadear comparações**: `a < b < c` é erro de
compilação (a maioria dos alunos espera "a < b e b < c"; a linguagem
recusa em vez de calcular silenciosamente `(a < b) < c`, que compararia
um `booleano` com `c`). Escreve-o por extenso:

```algo
inicio
    a:inteiro = 1
    b:inteiro = 5
    c:inteiro = 10
    // se a < b < c entao         // ERRO de compilação
    se a < b e b < c entao
        escrever("está entre")
```

## 2.3 Lógicos

`e`  `ou`  `nao` — só operam sobre `booleano`, devolvem `booleano`.
`e`/`ou` têm curto-circuito: o lado direito só é avaliado se o esquerdo
não decidir já o resultado (`falso e X` nunca avalia `X`; `verdadeiro ou
X` nunca avalia `X`). Útil para evitar um erro em runtime:

```algo
inicio
    v:inteiro[5] = {1, 2, 3, 4, 5}
    i:inteiro = 7
    se i < 5 e v[i] > 0 entao      // 'v[i]' só é avaliado se 'i < 5'
        escrever("dentro dos limites")
    senao
        escrever("fora dos limites, ou índice inválido")
```

`nao` aplica-se a toda a comparação seguinte, não só ao valor
imediatamente a seguir: `nao a == b` é `nao (a == b)`, não `(nao a) ==
b` (que nem compilaria, já que `nao` só aceita `booleano`).

## 2.4 Potência (`^`)

`^` é associativo **à direita**: `2^3^2` calcula-se como `2^(3^2)`, não
`(2^3)^2`.

O tipo do resultado de `^` só é `inteiro` quando o compilador consegue
provar, só a partir do próprio código-fonte, que o expoente nunca é
negativo — caso contrário fica `decimal` (razão: `**` do Python devolve
`float` quando a base é `int` e o expoente é negativo, e a linguagem
tem de decidir o tipo do resultado em compilação, antes de saber o
valor do expoente em runtime). Isto acontece quando o expoente é um
literal não-negativo ou uma expressão feita só de literais/`constante`
combinados com `+`/`-`/`*`/`^` (incluindo encadeado, ex.: `2^3^2` — o
expoente `3^2` também é dobrado em compilação):

```algo
inicio
    escrever(2^10)          // 1024      (inteiro -- expoente é literal)
    escrever(2^3^2)         // 512       (inteiro -- expoente '3^2' também é literal)

    n:inteiro = 3
    escrever(2^n)           // decimal, mesmo sabendo 'n' positivo
    // x:inteiro = 2^n      // ERRO de compilação: 'decimal' não cabe em 'inteiro'
    x:decimal = 2^n         // certo
```

Se precisares de um resultado `inteiro` a partir de uma potência com
expoente não-literal (e souberes que o expoente nunca é negativo), passa
por `conversao.paraInteiro(2^n)` (capítulo 8) — o valor já é
numericamente inteiro nesse caso, só o *tipo* declarado em ALGO é que
fica `decimal`.

## 2.5 Precedência (do que liga primeiro para o que liga por último)

| Nível | Operadores | Associatividade |
|---|---|---|
| 1 (mais apertado) | `^` | direita |
| 2 | `-` unário | -- |
| 3 | `*` `/` `div` `mod` | esquerda |
| 4 | `+` `-` (binários) | esquerda |
| 5 | `==` `<>` `<` `>` `<=` `>=` | não encadeável (2.2) |
| 6 | `nao` | -- |
| 7 | `e` | esquerda |
| 8 (mais solto) | `ou` | esquerda |

`-` unário liga mais apertado que `*`/`/` mas mais solto que `^`:

```algo
inicio
    escrever(-2^2)          // -4   -- '^' primeiro: -(2^2), não (-2)^2
    escrever(-2 * 3)        // -6   -- '-' unário antes de '*'
```

Usa parênteses sempre que a ordem não for óbvia à primeira leitura —
não há penalização por parênteses a mais, só por dúvida a mais.

## Exemplo completo

```algo
algoritmo "MediaEClassificacao"

inicio
    n1:decimal
    n2:decimal
    escrever("Nota 1: ")
    ler(n1)
    escrever("Nota 2: ")
    ler(n2)

    media:decimal = (n1 + n2) / 2
    aprovado:booleano = media >= 9.5 e n1 >= 5.0 e n2 >= 5.0

    escrever("Média: ", media)
    escrever("Aprovado: ", aprovado)
```
