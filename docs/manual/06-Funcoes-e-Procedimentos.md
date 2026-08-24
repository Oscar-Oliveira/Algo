# 6. Funções e procedimentos

## 6.1 `funcao` vs. `procedimento`

- `funcao` devolve sempre um valor — declara o tipo depois dos
  parâmetros, e todo caminho de execução tem de acabar num `retornar
  <expressão>`.
- `procedimento` não devolve valor nenhum — sem tipo de retorno, e
  `retornar` (sem expressão) é opcional, só para sair mais cedo.

```algo
algoritmo "Exemplo"

funcao dobro(x:inteiro):inteiro
    retornar x * 2

procedimento saudar(nome:cadeia)
    escrever("Olá, ", nome, "!")

inicio
    escrever(dobro(21))
    saudar("Rita")
```

Ambos são declarados fora de `inicio`, antes do bloco principal, e
podem ser chamados de qualquer sítio do programa (incluindo antes de
onde estão definidos no ficheiro, e umas dentro das outras
recursivamente — ver 6.5).

## 6.2 Parâmetros por valor (padrão)

Sem `ref`, um parâmetro é uma **cópia** — alterar o parâmetro dentro da
função nunca afeta a variável do chamador (mesma regra de cópia por
valor que uma atribuição normal, capítulo 5). O tipo do argumento só
precisa de ser *compatível* com o do parâmetro, não exatamente igual —
as mesmas promoções de sempre (`inteiro` → `decimal`, `caracter` →
`cadeia`):

```algo
funcao meio(x:decimal):decimal
    retornar x / 2

inicio
    escrever(meio(5))     // 2.5 -- '5' (inteiro) promovido a 'decimal'
```

## 6.3 Parâmetros por referência (`ref`)

`ref` faz o parâmetro apontar para a MESMA variável do chamador — uma
alteração dentro da função é visível fora dela depois da chamada
terminar. É a única forma de uma função "devolver" mais do que um
valor, ou de mudar diretamente uma variável do chamador:

```algo
procedimento trocar(ref a:inteiro, ref b:inteiro)
    tmp:inteiro = a
    a = b
    b = tmp

inicio
    x:inteiro = 1
    y:inteiro = 2
    trocar(x, y)
    escrever(x, " ", y)        // 2 1
```

Regras específicas de `ref`, mais estritas do que um parâmetro normal:

- O argumento tem de ser **uma variável, um elemento de vetor, ou um
  campo de estrutura** — nunca uma expressão calculada (`inc(x + 1)` é
  erro de compilação) nem uma `constante`.
- O tipo do argumento tem de ser **exatamente igual** ao do parâmetro —
  sem promoção nenhuma (passar um `inteiro` a um `ref x:decimal` é erro,
  ao contrário de um parâmetro por valor). Faz sentido: o valor final é
  escrito de volta na variável do chamador, que só pode guardar o seu
  próprio tipo declarado.
- A mesma variável não pode ser passada por `ref` duas vezes na mesma
  chamada (ex.: `trocar(x, x)`) — ficaria ambíguo qual das duas
  escritas "ganha".
- Uma chamada a uma função/procedimento com **algum** parâmetro `ref`
  só pode ser usada como instrução isolada (`inc(x)`) ou do lado
  direito de uma atribuição/declaração (`y = inc(x)`) — nunca dentro de
  uma expressão maior (`escrever(inc(x))` é erro de compilação; usa
  `inc(x)` numa linha e `escrever(x)` na seguinte).

## 6.4 Variáveis globais dentro de uma função

Uma função pode **ler e escrever diretamente** uma variável global
(declarada antes de `inicio`, fora de qualquer função — capítulo 1),
sem precisar de `ref` nem de nenhuma sintaxe especial:

```algo
algoritmo "Contador"

contador:inteiro = 0

procedimento incrementaContador()
    contador = contador + 1

inicio
    incrementaContador()
    incrementaContador()
    escrever(contador)    // 2
```

Uma variável local (parâmetro, ou declarada dentro do corpo da função)
com o mesmo nome de uma global **sombreia-a** dentro dessa função —
deixa de ser possível lá dentro aceder à global com esse nome. Uma
`constante` global continua imutável mesmo lida de dentro de uma
função (não pode ser reatribuída, só lida).

## 6.5 Recursão

Uma função pode chamar-se a si própria normalmente:

```algo
funcao fatorial(n:inteiro):inteiro
    se n <= 1 entao
        retornar 1
    retornar n * fatorial(n - 1)
```

## 6.6 Nem todo o caminho pode "esquecer-se" de `retornar`

O compilador rejeita uma `funcao` em que algum caminho de execução
chegue ao fim sem passar por `retornar` — mas essa verificação é
**deliberadamente conservadora**: um `se` sem `senao` nunca conta como
garantidamente terminando em `retornar`, mesmo que, olhando para a
lógica, os casos cobertos esgotem todos os valores possíveis:

```algo
funcao sinal(x:inteiro):inteiro
    se x > 0 entao
        retornar 1
    senao se x < 0 entao
        retornar -1
    // ERRO de compilação: falta o caso x == 0
```

O compilador não sabe (nem tenta provar) que não existe nenhum outro
valor de `x` — só sabe que não há `senao`. A correção é sempre
explícita: acrescenta um `senao`/`contrario` que cubra o resto.

## 6.7 Vetor como parâmetro

Um parâmetro do tipo vetor usa colchetes **vazios** — `v:tipo[]` — e
aceita um vetor de qualquer tamanho (por isso é comum passar também o
tamanho, ou o próprio vetor incluir uma posição-sentinela, consoante o
problema):

```algo
funcao soma(v:inteiro[], tamanho:inteiro):inteiro
    total:inteiro = 0
    i:inteiro
    para i de 0 ate tamanho - 1 fazer
        total = total + v[i]
    retornar total

inicio
    numeros:inteiro[4] = {1, 2, 3, 4}
    escrever(soma(numeros, 4))     // 10
```

O tipo do elemento tem de ser **exatamente igual** ao declarado no
parâmetro (sem promoção `inteiro`→`decimal`, nem por valor nem por
`ref`) — um vetor não é alargado elemento a elemento só para caber
noutro parâmetro. Um vetor passado por valor (sem `ref`) continua a ser
copiado inteiro para dentro da função (capítulo 5) — `soma` acima
podia mutar `v` livremente sem afetar `numeros` no chamador.

## Exemplo completo

```algo
algoritmo "MaiorDivisorComum"

funcao mdc(a:inteiro, b:inteiro):inteiro
    se b == 0 entao
        retornar a
    retornar mdc(b, a mod b)

procedimento mostrarFracaoSimplificada(ref numerador:inteiro, ref denominador:inteiro)
    d:inteiro = mdc(numerador, denominador)
    numerador = numerador div d
    denominador = denominador div d

inicio
    n:inteiro
    d:inteiro
    escrever("Numerador: ")
    ler(n)
    escrever("Denominador: ")
    ler(d)

    mostrarFracaoSimplificada(n, d)
    escrever("Fração simplificada: ", n, "/", d)
```
