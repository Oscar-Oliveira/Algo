# 10. `afirmar` e tratamento de erros

## 10.1 `afirmar`

`afirmar <condição booleana>[, <mensagem de texto>]` verifica uma
condição enquanto o programa corre — se for falsa, o programa para
imediatamente com uma mensagem que mostra a própria condição (e a tua
mensagem, se deste uma):

```algo
inicio
    idade:inteiro = 5
    afirmar idade >= 18, "idade tem de ser maior ou igual a 18"
```

Saída (e o programa para, código de saída `1`; `N` é a linha exata do
`afirmar` no ficheiro `.algo` completo, incluindo o cabeçalho
`algoritmo "..."` que este excerto omite):

```
❌ Afirmação falhou (linha N): idade >= 18 — idade tem de ser maior ou igual a 18
```

Sem mensagem, mostra só a condição:

```algo
inicio
    idade:inteiro = 5
    afirmar idade >= 18
```

```
❌ Afirmação falhou (linha N): idade >= 18
```

Usa-se sobretudo para validar as tuas próprias suposições enquanto
escreves/testas um exercício ("isto nunca deveria acontecer, se
acontecer quero saber já") — ao contrário de `assert` em Python,
**nunca é desativado/ignorado** (não há um "modo otimizado" que o
remova); um `afirmar` fica sempre ativo no programa final.

## 10.2 Erros em tempo de execução

Um erro que só pode ser detetado ao correr o programa (não em
compilação) — índice fora dos limites, divisão por zero, valor
inválido para converter, etc. — nunca aparece como um *traceback* cru
do Python. O programa imprime sempre uma mensagem em português no
formato `Erro em tempo de execução: <explicação>. (linha N)` e termina
com código de saída `1`.

| Situação | Mensagem |
|---|---|
| índice de **vetor** fora dos limites (inclui negativo) | "tentaste aceder a uma posição de vetor que não existe (índice fora dos limites)." |
| índice de **texto** fora dos limites (`cadeia.caracter`, etc.) | "tentaste aceder a uma posição de texto que não existe (índice fora dos limites)." |
| divisão (`/`, `div`, `mod`) por zero | "divisão por zero." |
| aceder a um campo de um valor `nulo` | "tentaste aceder ao campo '\<nome\>' de um valor nulo." |
| indexar (`v[i]`) um **vetor** `nulo` | "tentaste aceder a uma posição de um vetor nulo." |
| dois argumentos `ref` que só colidem para certos índices (ex. `trocar(v[i], v[j])` com `i == j` em runtime — capítulo 6) | "'\<expr1\>' e '\<expr2\>' referem-se à mesma posição em runtime -- não podem ser ambos passados por referência na mesma chamada a '\<função\>'." |
| `ler()` depois de esgotar o ficheiro/entrada disponível | "o programa tentou ler mais valores do que os que o ficheiro de entradas tinha." |
| resultado grande demais para representar | "o resultado é grande demais para ser representado (overflow numérico)." |
| recursão sem caso base (nunca para) | "recursão infinita (a função nunca chega ao caso base)." |
| pedido de memória grande demais (ex.: vetor enorme) | "o programa ficou sem memória (o valor pedido é grande demais)." |
| uma conversão/operação recebe um valor que não faz sentido (ex. `matematica.raiz(-1)`, `conversao.paraInteiro("abc")`) | mensagem específica da biblioteca, já em português (capítulo 8), ou um genérico "valor inválido (...)" quando não há tradução dedicada |

```algo
inicio
    x:inteiro = 5
    y:inteiro = 0
    escrever(x div y)
```

```
Erro em tempo de execução: divisão por zero. (linha N)
```

## 10.3 `afirmar` vs. erro em runtime vs. erro de compilação

Três tipos de problema, três momentos diferentes:

| Tipo | Quando é detetado | Exemplo |
|---|---|---|
| Erro de **compilação** | antes de o programa correr, sempre | `idade:inteiro = "vinte"` (tipos incompatíveis) |
| Erro em **runtime** | a meio da execução, causado pelos dados concretos | `v[10]` num vetor de tamanho 5 |
| `afirmar` falhado | a meio da execução, é uma verificação **tua**, não do compilador | `afirmar idade >= 0` |

Um erro de compilação acontece sempre da mesma forma, independentemente
da entrada do programa — o compilador não corre nada, só lê o código.
Um erro em runtime e um `afirmar` falhado só acontecem com certos
valores concretos (ex.: só se o utilizador introduzir `0`); a diferença
entre os dois é que um erro em runtime vem de uma operação que a
própria linguagem já sabe que pode falhar (divisão, índice, ...), e um
`afirmar` é uma condição que **tu** decidiste que tinha de ser
verdadeira naquele ponto do programa.

## Exemplo completo

```algo
algoritmo "DivisorSeguro"

funcao dividir(a:decimal, b:decimal):decimal
    afirmar b <> 0.0, "não é possível dividir por zero"
    retornar a / b

inicio
    a:decimal
    b:decimal
    escrever("Numerador: ")
    ler(a)
    escrever("Denominador: ")
    ler(b)
    escrever(dividir(a, b))
```

Com `b = 0`, o `afirmar` dentro de `dividir` para o programa com uma
mensagem clara — antes mesmo de chegar à divisão que geraria o erro em
runtime genérico "divisão por zero." Nenhuma das duas formas deixa o
programa continuar com um resultado sem sentido.
